"""Services for reading and updating company-wide timesheet configuration."""

import re
from copy import deepcopy
from typing import Any
from zoneinfo import available_timezones

from django.db import transaction

from apps.audit.services import record_audit_event
from common.exceptions import DomainError

from .models import CompanySetting

ALLOWED_INCREMENTS = {5, 6, 15, 30, 60}
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

DEFAULT_SETTINGS: dict[str, Any] = {
    "week_start_day": 0,  # 0 = Monday .. 6 = Sunday
    "default_timezone": "UTC",
    "expected_daily_minutes": 480,
    "expected_weekly_minutes": 2400,
    "entry_increment_minutes": 15,
    "max_daily_minutes": 960,
    "submission_deadline_day": 4,  # Friday
    "submission_deadline_time": "17:00",
    "allow_billable_override": False,
    "allow_duplicate_entries": False,
    "allow_self_approval": False,
    "allow_overlapping_assignments": True,
    "require_minimum_hours_on_submit": False,
    "max_export_rows": 50000,
    "sap_modules": [
        "FI",
        "CO",
        "MM",
        "SD",
        "PP",
        "HCM",
        "SuccessFactors",
        "ABAP",
        "Basis",
        "BTP",
        "Analytics",
        "S/4HANA Migration",
    ],
    "sap_workstreams": [
        "Discovery",
        "Design",
        "Build & Config",
        "Data Migration",
        "Testing",
        "Cutover",
        "Hypercare",
        "Internal",
    ],
}


def get_settings() -> dict[str, Any]:
    """Returns effective company settings merged over baseline defaults."""
    effective = deepcopy(DEFAULT_SETTINGS)
    for row in CompanySetting.objects.all():
        if row.key in effective:
            effective[row.key] = row.value
    return effective


def update_settings(*, actor: Any, updates: dict[str, Any]) -> dict[str, Any]:
    """Validates and updates company settings with an audit log entry."""
    before = get_settings()
    candidate = deepcopy(before)

    unknown = set(updates.keys()) - set(DEFAULT_SETTINGS.keys())
    if unknown:
        raise DomainError(
            code="VALIDATION_ERROR",
            message=f"Unsupported setting key(s): {', '.join(sorted(unknown))}",
            status_code=400,
        )

    for key, val in updates.items():
        if key == "entry_increment_minutes" and val not in ALLOWED_INCREMENTS:
            raise DomainError(
                code="VALIDATION_ERROR",
                message=f"entry_increment_minutes must be one of {sorted(ALLOWED_INCREMENTS)}.",
                details=[{"field": "entry_increment_minutes", "issue": "invalid_increment"}],
            )
        elif key in {"week_start_day", "submission_deadline_day"}:
            if not isinstance(val, int) or isinstance(val, bool) or not (0 <= val <= 6):
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message=f"{key} must be an integer between 0 (Monday) and 6 (Sunday).",
                    details=[{"field": key, "issue": "out_of_range"}],
                )
        elif key == "default_timezone":
            if val not in available_timezones():
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message=f"Unknown IANA timezone '{val}'.",
                    details=[{"field": "default_timezone", "issue": "invalid_timezone"}],
                )
        elif key == "submission_deadline_time":
            if not isinstance(val, str) or not _TIME_RE.match(val):
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message="submission_deadline_time must use 24-hour HH:MM format.",
                    details=[{"field": "submission_deadline_time", "issue": "invalid_format"}],
                )
        elif key in {"sap_modules", "sap_workstreams"}:
            if not isinstance(val, list) or not val or not all(isinstance(x, str) and x.strip() for x in val):
                raise DomainError(
                    code="VALIDATION_ERROR",
                    message=f"{key} must be a non-empty list of strings.",
                    details=[{"field": key, "issue": "invalid_taxonomy"}],
                )
            deduped: list[str] = []
            seen: set[str] = set()
            for item in val:
                cleaned = item.strip()
                if cleaned.lower() not in seen:
                    seen.add(cleaned.lower())
                    deduped.append(cleaned)
            val = deduped
        candidate[key] = val

    if candidate["max_daily_minutes"] < candidate["expected_daily_minutes"]:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="max_daily_minutes cannot be less than expected_daily_minutes.",
            details=[{"field": "max_daily_minutes", "issue": "below_expected_daily"}],
        )

    with transaction.atomic():
        for key in updates:
            CompanySetting.objects.update_or_create(
                key=key,
                defaults={"value": candidate[key], "updated_by": actor},
            )
        record_audit_event(
            actor=actor,
            action="SETTINGS_UPDATED",
            entity_type="CompanySetting",
            entity_id="global",
            before_json=before,
            after_json=candidate,
        )
    return candidate
