"""Transactional approval, rejection, and reopen workflow services (SRS §6.3)."""

from typing import Any

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_audit_event
from apps.notifications.models import Notification
from apps.notifications.services import emit_notification
from apps.settings_app.services import get_settings
from apps.timesheets.models import Timesheet
from apps.timesheets.services import scoped_timesheets_queryset
from common.concurrency import check_concurrency
from common.exceptions import DomainError

from .models import ApprovalEvent


def _can_approve_or_reject(actor: User, timesheet: Timesheet, settings_dict: dict[str, Any]) -> bool:
    if timesheet.user_id == actor.id and not settings_dict.get("allow_self_approval", False):
        return False
    if actor.role == User.Role.ADMIN:
        return True
    if actor.role == User.Role.APPROVER:
        if timesheet.assigned_approver_id is not None:
            return timesheet.assigned_approver_id == actor.id
        return timesheet.user.manager_id == actor.id
    return False


def _validate_reason(raw_reason: Any) -> str:
    cleaned = (raw_reason or "").strip() if isinstance(raw_reason, str) else ""
    if not cleaned or len(cleaned) > 1000:
        raise DomainError(
            code="APPROVAL_REASON_REQUIRED",
            message="A non-empty reason (1 to 1000 characters) is required.",
            status_code=400,
            details=[{"field": "reason", "issue": "required"}],
        )
    return cleaned


def pending_approvals_queryset(actor: User):
    if actor.role not in {User.Role.ADMIN, User.Role.APPROVER}:
        raise DomainError(
            code="AUTH_FORBIDDEN",
            message="You do not have permission to view the approval queue.",
            status_code=403,
        )

    settings_dict = get_settings()
    qs = (
        Timesheet.objects.filter(status=Timesheet.Status.SUBMITTED)
        .select_related("user", "assigned_approver")
        .prefetch_related("entries__project", "entries__task", "approval_events__actor")
    )
    if actor.role == User.Role.APPROVER:
        qs = qs.filter(assigned_approver=actor)
    if not settings_dict.get("allow_self_approval", False):
        qs = qs.exclude(user=actor)
    return qs


def approve_timesheet(
    *,
    actor: User,
    request: Any,
    timesheet: Timesheet,
    expected_version: int | None = None,
) -> Timesheet:
    settings_dict = get_settings()

    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().select_related("user").get(id=timesheet.id)
        if not _can_approve_or_reject(actor, locked, settings_dict):
            raise DomainError(
                code="APPROVER_OUT_OF_SCOPE",
                message="You are not authorized to approve this timesheet.",
                status_code=403,
            )

        check_concurrency(request, "timesheet", locked, expected_version)

        if locked.status != Timesheet.Status.SUBMITTED:
            raise DomainError(
                code="TS_NOT_SUBMITTED",
                message=f"Timesheet must be in SUBMITTED status to approve (current: {locked.status}).",
                status_code=409,
            )

        locked.status = Timesheet.Status.APPROVED
        locked.approved_at = timezone.now()
        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        ApprovalEvent.objects.create(
            timesheet=locked,
            actor=actor,
            action=ApprovalEvent.Action.APPROVED,
            reason=None,
        )
        record_audit_event(
            actor=actor,
            action="TIMESHEET_APPROVED",
            entity_type="Timesheet",
            entity_id=locked.id,
            before_json={"status": Timesheet.Status.SUBMITTED},
            after_json={"status": locked.status, "approved_at": locked.approved_at.isoformat()},
        )
        emit_notification(
            user=locked.user,
            notification_type=Notification.Type.TIMESHEET_APPROVED,
            title=f"Timesheet approved ({locked.period_start} to {locked.period_end})",
            payload={
                "timesheet_id": str(locked.id),
                "period_start": str(locked.period_start),
                "period_end": str(locked.period_end),
                "approver_name": actor.full_name,
                "approved_at": locked.approved_at.isoformat(),
            },
            email_subject=f"Timesheet approved: {locked.period_start} to {locked.period_end}",
            email_body=(
                f"Your timesheet for {locked.period_start} to {locked.period_end} was approved "
                f"by {actor.full_name} at {locked.approved_at.isoformat()}."
            ),
        )
        return scoped_timesheets_queryset(actor).get(id=locked.id)


def reject_timesheet(
    *,
    actor: User,
    request: Any,
    timesheet: Timesheet,
    reason: Any,
    expected_version: int | None = None,
) -> Timesheet:
    cleaned_reason = _validate_reason(reason)
    settings_dict = get_settings()

    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().select_related("user").get(id=timesheet.id)
        if not _can_approve_or_reject(actor, locked, settings_dict):
            raise DomainError(
                code="APPROVER_OUT_OF_SCOPE",
                message="You are not authorized to reject this timesheet.",
                status_code=403,
            )

        check_concurrency(request, "timesheet", locked, expected_version)

        if locked.status != Timesheet.Status.SUBMITTED:
            raise DomainError(
                code="TS_NOT_SUBMITTED",
                message=f"Timesheet must be in SUBMITTED status to reject (current: {locked.status}).",
                status_code=409,
            )

        locked.status = Timesheet.Status.REJECTED
        locked.approved_at = None
        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        ApprovalEvent.objects.create(
            timesheet=locked,
            actor=actor,
            action=ApprovalEvent.Action.REJECTED,
            reason=cleaned_reason,
        )
        record_audit_event(
            actor=actor,
            action="TIMESHEET_REJECTED",
            entity_type="Timesheet",
            entity_id=locked.id,
            before_json={"status": Timesheet.Status.SUBMITTED},
            after_json={"status": locked.status, "reason": cleaned_reason},
        )
        emit_notification(
            user=locked.user,
            notification_type=Notification.Type.TIMESHEET_REJECTED,
            title=f"Timesheet returned for correction ({locked.period_start} to {locked.period_end})",
            payload={
                "timesheet_id": str(locked.id),
                "period_start": str(locked.period_start),
                "period_end": str(locked.period_end),
                "approver_name": actor.full_name,
                "reason": cleaned_reason,
            },
            email_subject=f"Timesheet returned: {locked.period_start} to {locked.period_end}",
            email_body=(
                f"Your timesheet for {locked.period_start} to {locked.period_end} was returned by "
                f"{actor.full_name}. Reason: {cleaned_reason}"
            ),
        )
        return scoped_timesheets_queryset(actor).get(id=locked.id)


def reopen_timesheet(
    *,
    actor: User,
    request: Any,
    timesheet: Timesheet,
    reason: Any,
    expected_version: int | None = None,
) -> Timesheet:
    cleaned_reason = _validate_reason(reason)
    settings_dict = get_settings()

    with transaction.atomic():
        locked = Timesheet.objects.select_for_update().select_related("user").get(id=timesheet.id)
        if not _can_approve_or_reject(actor, locked, settings_dict):
            raise DomainError(
                code="AUTH_FORBIDDEN",
                message="You do not have permission to reopen this timesheet.",
                status_code=403,
            )

        check_concurrency(request, "timesheet", locked, expected_version)

        if locked.status not in {Timesheet.Status.APPROVED, Timesheet.Status.SUBMITTED}:
            raise DomainError(
                code="TS_STATE_CONFLICT",
                message=f"Only SUBMITTED or APPROVED timesheets can be reopened (current: {locked.status}).",
                status_code=409,
            )

        previous_status = locked.status
        locked.status = Timesheet.Status.REOPENED
        locked.approved_at = None
        locked.version = F("version") + 1
        locked.save()
        locked.refresh_from_db()

        ApprovalEvent.objects.create(
            timesheet=locked,
            actor=actor,
            action=ApprovalEvent.Action.REOPENED,
            reason=cleaned_reason,
        )
        record_audit_event(
            actor=actor,
            action="TIMESHEET_REOPENED",
            entity_type="Timesheet",
            entity_id=locked.id,
            before_json={"status": previous_status},
            after_json={"status": locked.status, "reason": cleaned_reason},
        )
        emit_notification(
            user=locked.user,
            notification_type=Notification.Type.TIMESHEET_REOPENED,
            title=f"Timesheet reopened ({locked.period_start} to {locked.period_end})",
            payload={
                "timesheet_id": str(locked.id),
                "period_start": str(locked.period_start),
                "period_end": str(locked.period_end),
                "actor_name": actor.full_name,
                "reason": cleaned_reason,
            },
            email_subject=f"Timesheet reopened: {locked.period_start} to {locked.period_end}",
            email_body=(
                f"Your timesheet for {locked.period_start} to {locked.period_end} was reopened by "
                f"{actor.full_name}. Reason: {cleaned_reason}"
            ),
        )
        return scoped_timesheets_queryset(actor).get(id=locked.id)
