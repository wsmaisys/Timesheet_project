"""Core domain business rules for timesheets and time entries (BR-001..BR-015)."""

from datetime import date
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import F, Q, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.assignments.models import ProjectAssignment
from apps.audit.services import record_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import emit_notification
from apps.projects.models import Project, Task
from apps.settings_app.services import get_settings
from common.concurrency import check_concurrency
from common.exceptions import DomainError

from .models import TimeEntry, Timesheet

EDITABLE_STATUSES = {
    Timesheet.Status.DRAFT,
    Timesheet.Status.REJECTED,
    Timesheet.Status.REOPENED,
}


def scoped_timesheets_queryset(actor: User):
    base = Timesheet.objects.select_related("user", "assigned_approver").prefetch_related(
        "entries__project",
        "entries__task",
        "approval_events__actor",
    )
    if actor.role == User.Role.ADMIN:
        return base
    if actor.role == User.Role.MANAGEMENT_VIEWER:
        if actor.department:
            return base.filter(Q(user=actor) | Q(user__department__iexact=actor.department))
        return base
    if actor.role == User.Role.APPROVER:
        return base.filter(
            Q(user=actor) | Q(assigned_approver=actor) | Q(user__manager=actor)
        ).distinct()
    return base.filter(user=actor)


def _assert_timesheet_owner_and_editable(actor: User, timesheet: Timesheet) -> None:
    if timesheet.user_id != actor.id:
        raise DomainError(
            code="AUTH_FORBIDDEN",
            message="You can only modify your own timesheet.",
            status_code=403,
        )
    if timesheet.status not in EDITABLE_STATUSES:
        raise DomainError(
            code="TS_NOT_EDITABLE",
            message=f"Timesheet in status '{timesheet.status}' cannot be edited.",
            status_code=409,
        )


def _validate_period_boundaries(period_start: date, period_end: date, settings_dict: dict[str, Any]) -> None:
    if period_end < period_start:
        raise DomainError(
            code="TS_PERIOD_INVALID",
            message="period_end cannot precede period_start.",
            status_code=400,
        )
    if (period_end - period_start).days != 6:
        raise DomainError(
            code="TS_PERIOD_INVALID",
            message="Timesheet period must span exactly 7 calendar days.",
            status_code=400,
        )
    expected_start_day = int(settings_dict.get("week_start_day", 0))
    if period_start.weekday() != expected_start_day:
        raise DomainError(
            code="TS_PERIOD_INVALID",
            message=f"period_start must start on configured week start weekday ({expected_start_day}).",
            status_code=400,
        )


def create_timesheet(*, actor: User, period_start: date, period_end: date, notes: str | None = None) -> Timesheet:
    settings_dict = get_settings()
    _validate_period_boundaries(period_start, period_end, settings_dict)

    if Timesheet.objects.filter(user=actor, period_start=period_start).exists():
        raise DomainError(
            code="TS_PERIOD_EXISTS",
            message=f"A timesheet already exists for period starting {period_start}.",
            status_code=409,
        )

    cleaned_notes = notes.strip() if isinstance(notes, str) and notes.strip() else None

    with transaction.atomic():
        try:
            timesheet = Timesheet.objects.create(
                user=actor,
                period_start=period_start,
                period_end=period_end,
                status=Timesheet.Status.DRAFT,
                notes=cleaned_notes,
            )
        except IntegrityError:
            raise DomainError(
                code="TS_PERIOD_EXISTS",
                message=f"A timesheet already exists for period starting {period_start}.",
                status_code=409,
            )

        record_audit_event(
            actor=actor,
            action="TIMESHEET_CREATED",
            entity_type="Timesheet",
            entity_id=timesheet.id,
            after_json={
                "period_start": str(timesheet.period_start),
                "period_end": str(timesheet.period_end),
                "status": timesheet.status,
            },
        )
        return scoped_timesheets_queryset(actor).get(id=timesheet.id)


def update_timesheet(
    *,
    actor: User,
    request: Any,
    timesheet: Timesheet,
    payload: dict[str, Any],
) -> Timesheet:
    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().get(id=timesheet.id)
        _assert_timesheet_owner_and_editable(actor, locked)
        check_concurrency(request, "timesheet", locked, payload.get("version"))

        before = {"notes": locked.notes, "version": locked.version}
        if "notes" in payload:
            raw_notes = payload["notes"]
            locked.notes = raw_notes.strip() if isinstance(raw_notes, str) and raw_notes.strip() else None

        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        record_audit_event(
            actor=actor,
            action="TIMESHEET_UPDATED",
            entity_type="Timesheet",
            entity_id=locked.id,
            before_json=before,
            after_json={"notes": locked.notes, "version": locked.version},
        )
        return scoped_timesheets_queryset(actor).get(id=locked.id)


def _validate_and_resolve_entry(
    *,
    actor: User,
    timesheet: Timesheet,
    work_date: date,
    project_id: Any,
    task_id: Any,
    duration_minutes: int,
    billable: bool,
    description: str,
    exclude_entry_id: Any = None,
) -> tuple[Project, Task, str]:
    settings_dict = get_settings()

    if work_date < timesheet.period_start or work_date > timesheet.period_end:
        raise DomainError(
            code="TS_ENTRY_DATE_OUTSIDE_PERIOD",
            message=(
                f"work_date {work_date} is outside timesheet period "
                f"{timesheet.period_start}..{timesheet.period_end}."
            ),
            status_code=400,
        )

    increment = int(settings_dict.get("entry_increment_minutes", 15))
    max_daily = int(settings_dict.get("max_daily_minutes", 960))
    if duration_minutes <= 0 or duration_minutes % increment != 0:
        raise DomainError(
            code="TS_ENTRY_INVALID_DURATION",
            message=f"Duration must be a positive multiple of {increment} minutes.",
            status_code=400,
            details=[{"field": "duration_minutes", "issue": "not_multiple_of_increment"}],
        )

    day_qs = TimeEntry.objects.filter(timesheet=timesheet, work_date=work_date)
    if exclude_entry_id is not None:
        day_qs = day_qs.exclude(id=exclude_entry_id)
    existing_day_minutes = day_qs.aggregate(total=Sum("duration_minutes"))["total"] or 0
    if existing_day_minutes + duration_minutes > max_daily:
        raise DomainError(
            code="TS_ENTRY_INVALID_DURATION",
            message=f"Total minutes for {work_date} cannot exceed configured daily maximum ({max_daily} minutes).",
            status_code=400,
            details=[{"field": "duration_minutes", "issue": "exceeds_daily_maximum"}],
        )

    project = Project.objects.filter(id=project_id).first()
    if project is None:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Selected project does not exist.",
            status_code=400,
            details=[{"field": "project_id", "issue": "not_found"}],
        )
    if project.status != Project.Status.ACTIVE:
        raise DomainError(
            code="PROJECT_INACTIVE",
            message=f"Project '{project.code}' is not active for time entry.",
            status_code=400,
        )

    task = Task.objects.filter(id=task_id).first()
    if task is None or task.project_id != project.id:
        raise DomainError(
            code="TASK_NOT_IN_PROJECT",
            message="Selected task does not belong to the chosen project.",
            status_code=400,
        )
    if task.status != Task.Status.ACTIVE:
        raise DomainError(
            code="PROJECT_INACTIVE",
            message=f"Task '{task.code}' is inactive.",
            status_code=400,
        )

    if not actor.can_override_assignment:
        has_assignment = (
            ProjectAssignment.objects.filter(
                user=actor,
                project=project,
                start_date__lte=work_date,
            )
            .filter(Q(end_date__isnull=True) | Q(end_date__gte=work_date))
            .exists()
        )
        if not has_assignment:
            raise DomainError(
                code="ASSIGNMENT_NOT_ACTIVE",
                message=f"You do not have an active assignment on project '{project.code}' for {work_date}.",
                status_code=400,
            )

    allow_billable_override = bool(settings_dict.get("allow_billable_override", False))
    if not allow_billable_override and bool(billable) != bool(project.billable_default):
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Company policy requires billable classification to match the project default.",
            status_code=400,
            details=[{"field": "billable", "issue": "override_not_permitted"}],
        )

    cleaned_desc = (description or "").strip()
    if not cleaned_desc or len(cleaned_desc) > 1000:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Work description must be between 1 and 1000 non-whitespace characters.",
            status_code=400,
            details=[{"field": "description", "issue": "invalid_description"}],
        )

    if not settings_dict.get("allow_duplicate_entries", False):
        dup_qs = TimeEntry.objects.filter(
            timesheet=timesheet,
            work_date=work_date,
            project=project,
            task=task,
            description__iexact=cleaned_desc,
        )
        if exclude_entry_id is not None:
            dup_qs = dup_qs.exclude(id=exclude_entry_id)
        if dup_qs.exists():
            raise DomainError(
                code="TS_ENTRY_DUPLICATE",
                message="Duplicate time entry detected for the same date, project, task, and description.",
                status_code=409,
            )

    return project, task, cleaned_desc


def add_time_entry(*, actor: User, timesheet: Timesheet, payload: dict[str, Any]) -> TimeEntry:
    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().get(id=timesheet.id)
        _assert_timesheet_owner_and_editable(actor, locked)

        project, task, cleaned_desc = _validate_and_resolve_entry(
            actor=actor,
            timesheet=locked,
            work_date=payload["work_date"],
            project_id=payload["project_id"],
            task_id=payload["task_id"],
            duration_minutes=payload["duration_minutes"],
            billable=payload["billable"],
            description=payload["description"],
        )

        entry = TimeEntry.objects.create(
            timesheet=locked,
            project=project,
            task=task,
            work_date=payload["work_date"],
            duration_minutes=payload["duration_minutes"],
            billable=payload["billable"],
            description=cleaned_desc,
        )
        locked.version = F("version") + 1
        locked.save(update_fields=["version", "updated_at"])

        record_audit_event(
            actor=actor,
            action="TIME_ENTRY_CREATED",
            entity_type="TimeEntry",
            entity_id=entry.id,
            after_json={
                "timesheet_id": str(locked.id),
                "work_date": str(entry.work_date),
                "project_id": str(project.id),
                "task_id": str(task.id),
                "duration_minutes": entry.duration_minutes,
                "billable": entry.billable,
            },
        )
        return TimeEntry.objects.select_related("project", "task").get(id=entry.id)


def update_time_entry(*, actor: User, timesheet: Timesheet, entry: TimeEntry, payload: dict[str, Any]) -> TimeEntry:
    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().get(id=timesheet.id)
        _assert_timesheet_owner_and_editable(actor, locked)
        if entry.timesheet_id != locked.id:
            raise DomainError("RESOURCE_NOT_FOUND", "Time entry does not belong to this timesheet.", status_code=404)

        before = {
            "work_date": str(entry.work_date),
            "project_id": str(entry.project_id),
            "task_id": str(entry.task_id),
            "duration_minutes": entry.duration_minutes,
            "billable": entry.billable,
            "description": entry.description,
        }

        work_date = payload.get("work_date", entry.work_date)
        project_id = payload.get("project_id", entry.project_id)
        task_id = payload.get("task_id", entry.task_id)
        duration_minutes = payload.get("duration_minutes", entry.duration_minutes)
        billable = payload.get("billable", entry.billable)
        description = payload.get("description", entry.description)

        project, task, cleaned_desc = _validate_and_resolve_entry(
            actor=actor,
            timesheet=locked,
            work_date=work_date,
            project_id=project_id,
            task_id=task_id,
            duration_minutes=duration_minutes,
            billable=billable,
            description=description,
            exclude_entry_id=entry.id,
        )

        entry.work_date = work_date
        entry.project = project
        entry.task = task
        entry.duration_minutes = duration_minutes
        entry.billable = billable
        entry.description = cleaned_desc
        entry.save()

        locked.version = F("version") + 1
        locked.save(update_fields=["version", "updated_at"])

        record_audit_event(
            actor=actor,
            action="TIME_ENTRY_UPDATED",
            entity_type="TimeEntry",
            entity_id=entry.id,
            before_json=before,
            after_json={
                "work_date": str(entry.work_date),
                "project_id": str(project.id),
                "task_id": str(task.id),
                "duration_minutes": entry.duration_minutes,
                "billable": entry.billable,
            },
        )
        return TimeEntry.objects.select_related("project", "task").get(id=entry.id)


def delete_time_entry(*, actor: User, timesheet: Timesheet, entry: TimeEntry) -> None:
    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().get(id=timesheet.id)
        _assert_timesheet_owner_and_editable(actor, locked)
        if entry.timesheet_id != locked.id:
            raise DomainError("RESOURCE_NOT_FOUND", "Time entry does not belong to this timesheet.", status_code=404)

        snapshot = {
            "timesheet_id": str(locked.id),
            "work_date": str(entry.work_date),
            "project_id": str(entry.project_id),
            "task_id": str(entry.task_id),
            "duration_minutes": entry.duration_minutes,
        }
        entry_id = entry.id
        entry.delete()

        locked.version = F("version") + 1
        locked.save(update_fields=["version", "updated_at"])

        record_audit_event(
            actor=actor,
            action="TIME_ENTRY_DELETED",
            entity_type="TimeEntry",
            entity_id=entry_id,
            before_json=snapshot,
        )


def submit_timesheet(
    *,
    actor: User,
    request: Any,
    timesheet: Timesheet,
    expected_version: int | None = None,
) -> Timesheet:
    settings_dict = get_settings()

    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().get(id=timesheet.id)
        if locked.user_id != actor.id:
            raise DomainError("AUTH_FORBIDDEN", "You can only submit your own timesheet.", status_code=403)

        check_concurrency(request, "timesheet", locked, expected_version)

        if locked.status in {Timesheet.Status.SUBMITTED, Timesheet.Status.APPROVED}:
            raise DomainError(
                code="TS_ALREADY_SUBMITTED",
                message=f"Timesheet is already in '{locked.status}' status.",
                status_code=409,
            )
        if locked.status not in EDITABLE_STATUSES:
            raise DomainError(
                code="TS_NOT_EDITABLE",
                message=f"Timesheet in status '{locked.status}' cannot be submitted.",
                status_code=409,
            )

        agg = locked.entries.aggregate(total=Sum("duration_minutes"))
        total_minutes = agg["total"] or 0
        if total_minutes <= 0:
            raise DomainError(
                code="TS_SUBMISSION_INCOMPLETE",
                message="Cannot submit a timesheet with no time entries.",
                status_code=400,
            )

        if settings_dict.get("require_minimum_hours_on_submit", False):
            expected_weekly = actor.expected_weekly_minutes or int(
                settings_dict.get("expected_weekly_minutes", 2400)
            )
            if total_minutes < expected_weekly:
                raise DomainError(
                    code="TS_SUBMISSION_INCOMPLETE",
                    message=f"Submission requires at least {expected_weekly} minutes (logged {total_minutes}).",
                    status_code=400,
                )

        before_status = locked.status
        approver = actor.manager if (actor.manager and actor.manager.status == User.Status.ACTIVE) else None
        locked.assigned_approver = approver
        locked.status = Timesheet.Status.SUBMITTED
        locked.submitted_at = timezone.now()
        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        record_audit_event(
            actor=actor,
            action="TIMESHEET_SUBMITTED",
            entity_type="Timesheet",
            entity_id=locked.id,
            before_json={"status": before_status},
            after_json={
                "status": locked.status,
                "total_minutes": total_minutes,
                "assigned_approver_id": str(approver.id) if approver else None,
            },
        )

        if approver is not None:
            emit_notification(
                user=approver,
                notification_type=Notification.Type.TIMESHEET_SUBMITTED,
                title=f"Timesheet submitted by {actor.full_name} ({locked.period_start} to {locked.period_end})",
                payload={
                    "timesheet_id": str(locked.id),
                    "employee_id": str(actor.id),
                    "employee_name": actor.full_name,
                    "period_start": str(locked.period_start),
                    "period_end": str(locked.period_end),
                    "total_minutes": total_minutes,
                },
                email_subject=f"Approval needed: {actor.full_name} timesheet ({locked.period_start})",
                email_body=(
                    f"{actor.full_name} submitted their timesheet for {locked.period_start} to {locked.period_end} "
                    f"({total_minutes // 60}h {total_minutes % 60:02d}m). Please review it in the approvals queue."
                ),
            )

        return scoped_timesheets_queryset(actor).get(id=locked.id)
