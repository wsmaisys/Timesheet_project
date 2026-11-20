"""Row-level scoped reporting, CSV export (with formula protection), and role dashboards."""

import csv
import io
from datetime import date, timedelta
from typing import Any

from django.db.models import Q, Sum
from django.utils import timezone

from apps.accounts.models import User
from apps.assignments.models import ProjectAssignment
from apps.notifications.models import Notification
from apps.projects.models import Project
from apps.settings_app.services import get_settings
from apps.timesheets.models import TimeEntry, Timesheet
from common.exceptions import DomainError

_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value: Any) -> str:
    """Neutralizes spreadsheet formula injection in exported CSV cells."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return f"'{text}"
    return text


def scoped_entries_queryset(actor: User):
    base = TimeEntry.objects.select_related("timesheet__user", "project").exclude(
        timesheet__status=Timesheet.Status.CANCELLED
    )
    if actor.role == User.Role.ADMIN:
        return base
    if actor.role == User.Role.MANAGEMENT_VIEWER:
        if actor.department:
            return base.filter(timesheet__user__department__iexact=actor.department)
        return base
    if actor.role == User.Role.APPROVER:
        return base.filter(
            Q(timesheet__user=actor)
            | Q(timesheet__user__manager=actor)
            | Q(timesheet__assigned_approver=actor)
            | Q(project__project_manager=actor)
        ).distinct()
    return base.filter(timesheet__user=actor)


def build_time_summary(
    *,
    actor: User,
    from_date: date,
    to_date: date,
    project_id: Any = None,
    user_id: Any = None,
    billable: bool | None = None,
    status: str | None = None,
) -> list[dict[str, Any]]:
    if to_date < from_date:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="to_date cannot precede from_date.",
            details=[{"field": "to_date", "issue": "before_from_date"}],
        )

    qs = scoped_entries_queryset(actor).filter(work_date__gte=from_date, work_date__lte=to_date)

    if project_id:
        qs = qs.filter(project_id=project_id)
    if user_id:
        qs = qs.filter(timesheet__user_id=user_id)
    if billable is not None:
        qs = qs.filter(billable=billable)
    if status:
        if status not in Timesheet.Status.values:
            raise DomainError("VALIDATION_ERROR", "Invalid timesheet status filter.")
        qs = qs.filter(timesheet__status=status)

    grouped = (
        qs.values(
            "timesheet__user_id",
            "timesheet__user__employee_code",
            "timesheet__user__full_name",
            "timesheet__user__department",
            "project_id",
            "project__code",
            "project__name",
            "billable",
        )
        .annotate(minutes=Sum("duration_minutes"))
        .order_by("timesheet__user__full_name", "project__code")
    )

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for item in grouped:
        key = (str(item["timesheet__user_id"]), str(item["project_id"]))
        if key not in merged:
            merged[key] = {
                "user_id": str(item["timesheet__user_id"]),
                "employee_code": item["timesheet__user__employee_code"],
                "employee_name": item["timesheet__user__full_name"],
                "department": item["timesheet__user__department"],
                "project_id": str(item["project_id"]),
                "project_code": item["project__code"],
                "project_name": item["project__name"],
                "billable_minutes": 0,
                "non_billable_minutes": 0,
                "total_minutes": 0,
            }
        mins = int(item["minutes"] or 0)
        if item["billable"]:
            merged[key]["billable_minutes"] += mins
        else:
            merged[key]["non_billable_minutes"] += mins
        merged[key]["total_minutes"] += mins

    return list(merged.values())


def export_time_summary_csv(
    *,
    actor: User,
    from_date: date,
    to_date: date,
    project_id: Any = None,
    user_id: Any = None,
    billable: bool | None = None,
    status: str | None = None,
) -> str:
    rows = build_time_summary(
        actor=actor,
        from_date=from_date,
        to_date=to_date,
        project_id=project_id,
        user_id=user_id,
        billable=billable,
        status=status,
    )
    max_rows = int(get_settings().get("max_export_rows", 50000))
    if len(rows) > max_rows:
        raise DomainError(
            code="EXPORT_TOO_LARGE",
            message=f"Export row count ({len(rows)}) exceeds maximum limit of {max_rows}.",
            status_code=400,
        )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "Employee Code",
            "Employee Name",
            "Department",
            "Project Code",
            "Project Name",
            "Billable Minutes",
            "Non-Billable Minutes",
            "Total Minutes",
            "Total Hours",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                sanitize_csv_cell(row["employee_code"]),
                sanitize_csv_cell(row["employee_name"]),
                sanitize_csv_cell(row["department"] or ""),
                sanitize_csv_cell(row["project_code"]),
                sanitize_csv_cell(row["project_name"]),
                row["billable_minutes"],
                row["non_billable_minutes"],
                row["total_minutes"],
                f"{row['total_minutes'] / 60:.2f}",
            ]
        )
    return buf.getvalue()


def _current_period_bounds(today: date, week_start_day: int) -> tuple[date, date]:
    offset = (today.weekday() - week_start_day) % 7
    period_start = today - timedelta(days=offset)
    return period_start, period_start + timedelta(days=6)


def build_dashboard_summary(actor: User) -> dict[str, Any]:
    settings_dict = get_settings()
    today = timezone.now().date()
    period_start, period_end = _current_period_bounds(today, int(settings_dict.get("week_start_day", 0)))
    expected_weekly = actor.expected_weekly_minutes or int(settings_dict.get("expected_weekly_minutes", 2400))

    own_current = (
        Timesheet.objects.filter(user=actor, period_start=period_start)
        .prefetch_related("entries")
        .first()
    )
    current_minutes = sum(e.duration_minutes for e in own_current.entries.all()) if own_current else 0
    returned_count = Timesheet.objects.filter(user=actor, status=Timesheet.Status.REJECTED).count()
    active_assignments_count = (
        ProjectAssignment.objects.filter(user=actor, start_date__lte=today)
        .filter(Q(end_date__isnull=True) | Q(end_date__gte=today))
        .count()
    )
    recent_weeks = [
        {
            "id": str(ts.id),
            "period_start": str(ts.period_start),
            "period_end": str(ts.period_end),
            "status": ts.status,
            "total_minutes": sum(e.duration_minutes for e in ts.entries.all()),
        }
        for ts in Timesheet.objects.filter(user=actor).prefetch_related("entries").order_by("-period_start")[:6]
    ]

    employee_summary = {
        "current_timesheet_id": str(own_current.id) if own_current else None,
        "current_status": own_current.status if own_current else "NOT_CREATED",
        "current_week_minutes": current_minutes,
        "expected_weekly_minutes": expected_weekly,
        "active_assignments_count": active_assignments_count,
        "returned_timesheets_count": returned_count,
        "unread_notifications_count": Notification.objects.filter(user=actor, read_at__isnull=True).count(),
        "recent_weeks": recent_weeks,
    }

    manager_summary = None
    if actor.role in {User.Role.APPROVER, User.Role.ADMIN}:
        team_users = User.objects.filter(manager=actor, status=User.Status.ACTIVE)
        pending_qs = Timesheet.objects.filter(status=Timesheet.Status.SUBMITTED)
        if actor.role == User.Role.APPROVER:
            pending_qs = pending_qs.filter(assigned_approver=actor)
        if not settings_dict.get("allow_self_approval", False):
            pending_qs = pending_qs.exclude(user=actor)

        team_current_submitted = Timesheet.objects.filter(
            user__in=team_users,
            period_start=period_start,
            status__in=[Timesheet.Status.SUBMITTED, Timesheet.Status.APPROVED],
        ).count()
        team_count = team_users.count()
        overdue_count = max(0, team_count - team_current_submitted)
        manager_summary = {
            "pending_approvals_count": pending_qs.count(),
            "direct_reports_count": team_count,
            "current_week_submitted_count": team_current_submitted,
            "current_week_missing_count": overdue_count,
        }

    admin_summary = None
    if actor.role == User.Role.ADMIN:
        soon_cutoff = today + timedelta(days=30)
        ending_soon = [
            {"id": str(p.id), "code": p.code, "name": p.name, "end_date": str(p.end_date)}
            for p in Project.objects.filter(
                status=Project.Status.ACTIVE,
                end_date__isnull=False,
                end_date__gte=today,
                end_date__lte=soon_cutoff,
            )[:5]
        ]
        admin_summary = {
            "active_users_count": User.objects.filter(status=User.Status.ACTIVE).count(),
            "active_projects_count": Project.objects.filter(status=Project.Status.ACTIVE).count(),
            "submitted_waiting_count": Timesheet.objects.filter(status=Timesheet.Status.SUBMITTED).count(),
            "projects_ending_soon": ending_soon,
        }

    management_summary = None
    if actor.role in {User.Role.MANAGEMENT_VIEWER, User.Role.ADMIN}:
        month_start = today.replace(day=1)
        summary_rows = build_time_summary(actor=actor, from_date=month_start, to_date=today)
        billable_total = sum(r["billable_minutes"] for r in summary_rows)
        non_billable_total = sum(r["non_billable_minutes"] for r in summary_rows)
        management_summary = {
            "month_start": str(month_start),
            "as_of_date": str(today),
            "billable_minutes": billable_total,
            "non_billable_minutes": non_billable_total,
            "total_minutes": billable_total + non_billable_total,
            "department_scope": actor.department or "ALL",
        }

    return {
        "role": actor.role,
        "current_period": {
            "period_start": str(period_start),
            "period_end": str(period_end),
            "week_start_day": settings_dict["week_start_day"],
            "entry_increment_minutes": settings_dict["entry_increment_minutes"],
        },
        "employee_summary": employee_summary,
        "manager_summary": manager_summary,
        "admin_summary": admin_summary,
        "management_summary": management_summary,
        "metric_definitions": {
            "hours_basis": "Sum of TimeEntry.duration_minutes divided by 60; stored exactly in integer minutes.",
            "date_basis": "TimeEntry.work_date (local calendar date YYYY-MM-DD in employee timezone).",
            "included_statuses": ["DRAFT", "SUBMITTED", "REJECTED", "APPROVED", "REOPENED"],
            "excluded_statuses": ["CANCELLED"],
            "scope_enforcement": "Row-level server-side RBAC + department scope on Management Viewer.",
        },
    }
