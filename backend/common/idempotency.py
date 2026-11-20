"""Idempotency-Key handling for retriable mutations (BR-015)."""

import hashlib
import json
from collections.abc import Callable
from typing import Any

from django.apps import apps
from django.db import IntegrityError, transaction
from rest_framework.response import Response

from .exceptions import DomainError


def _hash_payload(data: Any) -> str:
    serialized = json.dumps(data if data is not None else {}, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def run_idempotent(request, action_fn: Callable[[], Response]) -> Response:
    """Executes `action_fn` once per (user, method, path, Idempotency-Key)."""
    key = (request.headers.get("Idempotency-Key") or "").strip()
    if not key:
        return action_fn()

    if len(key) > 128:
        raise DomainError(
            code="VALIDATION_ERROR",
            message="Idempotency-Key header cannot exceed 128 characters.",
            status_code=400,
        )

    IdempotencyRecord = apps.get_model("timesheets", "IdempotencyRecord")
    request_hash = _hash_payload(getattr(request, "data", {}))
    lookup = {
        "user": request.user,
        "key": key,
        "method": request.method.upper(),
        "path": request.path,
    }

    existing = IdempotencyRecord.objects.filter(**lookup).first()
    if existing is not None:
        if existing.request_hash != request_hash:
            raise DomainError(
                code="TS_STATE_CONFLICT",
                message="Idempotency-Key already used with a different request payload.",
                status_code=409,
            )
        resp = Response(existing.response_body, status=existing.status_code)
        resp["X-Idempotent-Replay"] = "true"
        return resp

    with transaction.atomic():
        response = action_fn()
        if 200 <= response.status_code < 300:
            try:
                IdempotencyRecord.objects.create(
                    **lookup,
                    request_hash=request_hash,
                    status_code=response.status_code,
                    response_body=response.data if response.data is not None else {},
                )
            except IntegrityError:
                existing = IdempotencyRecord.objects.filter(**lookup).first()
                if existing is not None and existing.request_hash == request_hash:
                    replay = Response(existing.response_body, status=existing.status_code)
                    replay["X-Idempotent-Replay"] = "true"
                    return replay
        return response
