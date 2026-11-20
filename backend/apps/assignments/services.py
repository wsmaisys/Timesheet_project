"""Domain services for employee-to-project assignments (FR-ASG-001, FR-ASG-002)."""

from datetime import date
from typing import Any

from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import emit_notification
from apps.projects.models import Project
from apps.settings_app.services import get_settings
from common.exceptions import DomainError

from .models import ProjectAssignment


def scoped_assignments_queryset(actor: User):
    base = ProjectAssignment.objects.select_related("user", "project")
    if actor.role in {User.Role.ADMIN, User.Role.MANAGEMENT_VIEWER}:
        return base
    if actor.role == User.Role.APPROVER:
        return base.filter(
            Q(user=actor) | Q(user__manager=actor) | Q(project__project_manager=actor)
        ).distinct()
    return base.filter(user=actor)


def _assert_can_manage_assignment(actor: User, project: Project) -> None:
    if actor.role == User.Role.ADMIN:
        return
    if actor.role == User.Role.APPROVER and project.project_manager_id == actor.id:
        return
    raise DomainError(
        code="AUTH_FORBIDDEN",
        message="Only administrators or the project manager can manage project assignments.",
        status_code=403,
    )


def _check_overlap(
    *,
    user: User,
    project: Project,
    start_date: date,
    end_date: date | None,
    exclude_id: Any = None,
) -> None:
    if get_settings().get("allow_overlapping_assignments", True):
        return

    qs = ProjectAssignment.objects.filter(user=user, project=project)
    if exclude_id is not None:
        qs = qs.exclude(id=exclude_id)

    for existing in qs:
        a_end = end_date or date.max
        b_end = existing.end_date or date.max
        if start_date <= b_end and existing.start_date <= a_end:
            raise DomainError(
                code="ASSIGNMENT_DATE_INVALID",
                message="Overlapping assignment dates for this employee and project are disabled by policy.",
                status_code=409,
            )


def create_assignment(*, actor: User, payload: dict[str, Any]) -> ProjectAssignment:
    project = Project.objects.filter(id=payload["project_id"]).first()
    if project is None:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Project does not exist.",
            details=[{"field": "project_id", "issue": "not_found"}],
        )

    _assert_can_manage_assignment(actor, project)

    if project.status == Project.Status.CLOSED:
        raise DomainError(
            code="PROJECT_INACTIVE",
            message="Cannot assign employees to a closed project.",
            status_code=409,
        )

    target_user = User.objects.filter(id=payload["user_id"]).first()
    if target_user is None or target_user.status != User.Status.ACTIVE:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Assigned user must exist and be active.",
            details=[{"field": "user_id", "issue": "inactive_or_not_found"}],
        )

    start_date = payload["start_date"]
    end_date = payload.get("end_date")
    if end_date is not None and end_date < start_date:
        raise DomainError(
            code="ASSIGNMENT_DATE_INVALID",
            message="Assignment end_date cannot precede start_date.",
            status_code=400,
        )

    _check_overlap(user=target_user, project=project, start_date=start_date, end_date=end_date)

    with transaction.atomic():
        assignment = ProjectAssignment.objects.create(
            user=target_user,
            project=project,
            start_date=start_date,
            end_date=end_date,
            allocation_percent=payload.get("allocation_percent"),
        )
        record_audit_event(
            actor=actor,
            action="ASSIGNMENT_CREATED",
            entity_type="ProjectAssignment",
            entity_id=assignment.id,
            after_json={
                "user_id": str(target_user.id),
                "project_id": str(project.id),
                "start_date": str(start_date),
                "end_date": str(end_date) if end_date else None,
                "allocation_percent": float(assignment.allocation_percent)
                if assignment.allocation_percent is not None
                else None,
            },
        )
        emit_notification(
            user=target_user,
            notification_type=Notification.Type.ASSIGNMENT_CHANGED,
            title=f"Assigned to project {project.code}",
            payload={
                "assignment_id": str(assignment.id),
                "project_id": str(project.id),
                "project_code": project.code,
                "project_name": project.name,
                "start_date": str(start_date),
                "end_date": str(end_date) if end_date else None,
            },
            email_subject=f"New project assignment: {project.code} ({project.name})",
            email_body=(
                f"You have been assigned to project {project.code} - {project.name} "
                f"effective {start_date} to {end_date or 'ongoing'}."
            ),
        )
        return assignment


def update_assignment(
    *,
    actor: User,
    assignment: ProjectAssignment,
    payload: dict[str, Any],
) -> ProjectAssignment:
    _assert_can_manage_assignment(actor, assignment.project)
    before = {
        "start_date": str(assignment.start_date),
        "end_date": str(assignment.end_date) if assignment.end_date else None,
        "allocation_percent": float(assignment.allocation_percent)
        if assignment.allocation_percent is not None
        else None,
    }

    start_date = payload.get("start_date", assignment.start_date)
    end_date = payload.get("end_date", assignment.end_date)
    if end_date is not None and end_date < start_date:
        raise DomainError(
            code="ASSIGNMENT_DATE_INVALID",
            message="Assignment end_date cannot precede start_date.",
            status_code=400,
        )

    _check_overlap(
        user=assignment.user,
        project=assignment.project,
        start_date=start_date,
        end_date=end_date,
        exclude_id=assignment.id,
    )

    with transaction.atomic():
        assignment.start_date = start_date
        assignment.end_date = end_date
        if "allocation_percent" in payload:
            assignment.allocation_percent = payload["allocation_percent"]
        assignment.save()
        record_audit_event(
            actor=actor,
            action="ASSIGNMENT_UPDATED",
            entity_type="ProjectAssignment",
            entity_id=assignment.id,
            before_json=before,
            after_json={
                "start_date": str(assignment.start_date),
                "end_date": str(assignment.end_date) if assignment.end_date else None,
                "allocation_percent": float(assignment.allocation_percent)
                if assignment.allocation_percent is not None
                else None,
            },
        )
        return assignment
