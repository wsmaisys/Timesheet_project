"""Service functions for recording immutable audit events."""

import json
from typing import Any

from common.logging import get_request_id

from .models import AuditEvent


def _json_safe(payload: Any) -> Any:
    if payload is None:
        return None
    return json.loads(json.dumps(payload, default=str))


def record_audit_event(
    *,
    actor: Any,
    action: str,
    entity_type: str,
    entity_id: Any,
    before_json: Any = None,
    after_json: Any = None,
    request_id: str | None = None,
) -> AuditEvent:
    actor_obj = actor if getattr(actor, "is_authenticated", False) else None
    actor_email = getattr(actor_obj, "email", None) or "system@timesheet.local"
    return AuditEvent.objects.create(
        actor=actor_obj,
        actor_email=actor_email,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        before_json=_json_safe(before_json),
        after_json=_json_safe(after_json),
        request_id=request_id or get_request_id(),
    )
