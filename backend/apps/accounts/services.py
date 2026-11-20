"""Business services for user lifecycle management (FR-USER-001, FR-USER-002)."""

import secrets
from typing import Any
from zoneinfo import available_timezones

from django.db import IntegrityError, transaction

from apps.audit.services import record_audit_event
from common.exceptions import DomainError

from .models import User

_ALLOWED_SELF_PATCH_FIELDS = {"full_name", "timezone"}


def _validate_timezone(tz_name: str) -> str:
    cleaned = (tz_name or "").strip()
    if cleaned not in available_timezones():
        raise DomainError(
            code="VALIDATION_ERROR",
            message=f"Invalid IANA timezone '{cleaned}'.",
            details=[{"field": "timezone", "issue": "invalid_timezone"}],
        )
    return cleaned


def _validate_manager(user: User | None, manager_id: Any) -> User | None:
    if manager_id is None:
        return None
    manager = User.objects.filter(id=manager_id).first()
    if manager is None:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Configured manager_id does not exist.",
            details=[{"field": "manager_id", "issue": "not_found"}],
        )
    if user is not None:
        if manager.id == user.id:
            raise DomainError(
                code="VALIDATION_ERROR",
                message="A user cannot be assigned as their own manager.",
                details=[{"field": "manager_id", "issue": "self_manager"}],
            )
        # Prevent manager cycles.
        cursor = manager
        visited = {user.id}
        while cursor is not None:
            if cursor.id in visited:
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message="Manager hierarchy cannot contain cycles.",
                    details=[{"field": "manager_id", "issue": "circular_hierarchy"}],
                )
            visited.add(cursor.id)
            cursor = cursor.manager
    return manager


def _snapshot_user(user: User) -> dict[str, Any]:
    return {
        "employee_code": user.employee_code,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "status": user.status,
        "manager_id": str(user.manager_id) if user.manager_id else None,
        "department": user.department,
        "timezone": user.timezone,
        "expected_daily_minutes": user.expected_daily_minutes,
        "expected_weekly_minutes": user.expected_weekly_minutes,
        "can_override_assignment": user.can_override_assignment,
    }


def create_user(*, actor: User, payload: dict[str, Any]) -> User:
    email = payload["email"].strip().lower()
    employee_code = payload["employee_code"].strip()
    full_name = payload["full_name"].strip()
    tz_name = _validate_timezone(payload.get("timezone", "UTC"))

    if not employee_code or not full_name:
        raise DomainError("VALIDATION_ERROR", "employee_code and full_name cannot be blank.")

    if User.objects.filter(email__iexact=email).exists():
        raise DomainError(
            code="USER_EMAIL_EXISTS",
            message=f"User with email '{email}' already exists.",
            status_code=409,
        )

    if User.objects.filter(employee_code__iexact=employee_code).exists():
        raise DomainError(
            code="VALIDATION_ERROR",
            message=f"User with employee_code '{employee_code}' already exists.",
            status_code=409,
            details=[{"field": "employee_code", "issue": "already_exists"}],
        )

    manager = _validate_manager(None, payload.get("manager_id"))
    raw_password = payload.get("password") or secrets.token_urlsafe(16)

    with transaction.atomic():
        try:
            user = User.objects.create_user(
                email=email,
                password=raw_password,
                employee_code=employee_code,
                full_name=full_name,
                role=payload["role"],
                status=User.Status.ACTIVE,
                manager=manager,
                department=(payload.get("department") or None),
                timezone=tz_name,
                expected_daily_minutes=payload.get("expected_daily_minutes"),
                expected_weekly_minutes=payload.get("expected_weekly_minutes"),
                can_override_assignment=bool(payload.get("can_override_assignment", False)),
            )
        except IntegrityError:
            raise DomainError(
                code="USER_EMAIL_EXISTS",
                message="User email or employee code already exists.",
                status_code=409,
            )

        record_audit_event(
            actor=actor,
            action="USER_CREATED",
            entity_type="User",
            entity_id=user.id,
            after_json=_snapshot_user(user),
        )
        return user


def update_user(*, actor: User, target: User, payload: dict[str, Any]) -> User:
    is_admin = actor.role == User.Role.ADMIN
    if not is_admin:
        if actor.id != target.id:
            raise DomainError(
                code="AUTH_FORBIDDEN",
                message="You do not have permission to update another user.",
                status_code=403,
            )
        disallowed = set(payload.keys()) - _ALLOWED_SELF_PATCH_FIELDS
        if disallowed:
            raise DomainError(
                code="AUTH_FORBIDDEN",
                message="Only administrators can modify role, status, or organization scope fields.",
                status_code=403,
            )

    before = _snapshot_user(target)
    with transaction.atomic():
        if "employee_code" in payload:
            code = payload["employee_code"].strip()
            if not code:
                raise DomainError("VALIDATION_ERROR", "employee_code cannot be empty.")
            if User.objects.filter(employee_code__iexact=code).exclude(id=target.id).exists():
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message=f"Employee code '{code}' is already in use.",
                    status_code=409,
                    details=[{"field": "employee_code", "issue": "already_exists"}],
                )
            target.employee_code = code

        if "full_name" in payload:
            cleaned = payload["full_name"].strip()
            if not cleaned:
                raise DomainError("VALIDATION_ERROR", "full_name cannot be empty.")
            target.full_name = cleaned

        if "timezone" in payload:
            target.timezone = _validate_timezone(payload["timezone"])

        if "role" in payload:
            target.role = payload["role"]
        if "status" in payload:
            target.status = payload["status"]
        if "manager_id" in payload:
            target.manager = _validate_manager(target, payload["manager_id"])
        if "department" in payload:
            dept = payload["department"]
            target.department = dept.strip() if isinstance(dept, str) and dept.strip() else None
        if "expected_daily_minutes" in payload:
            target.expected_daily_minutes = payload["expected_daily_minutes"]
        if "expected_weekly_minutes" in payload:
            target.expected_weekly_minutes = payload["expected_weekly_minutes"]
        if "can_override_assignment" in payload:
            target.can_override_assignment = bool(payload["can_override_assignment"])

        target.save()
        record_audit_event(
            actor=actor,
            action="USER_UPDATED",
            entity_type="User",
            entity_id=target.id,
            before_json=before,
            after_json=_snapshot_user(target),
        )
        return target
