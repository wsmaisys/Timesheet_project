"""Optimistic concurrency helpers via ETag / If-Match and version field."""

from typing import Any

from .exceptions import DomainError


def make_etag(entity: str, entity_id: Any, version: int) -> str:
    return f'"{entity}-{entity_id}-v{version}"'


def _parse_if_match_version(header_val: str, entity: str, entity_id: Any) -> int | None:
    cleaned = header_val.strip()
    if cleaned.startswith("W/"):
        cleaned = cleaned[2:].strip()
    if len(cleaned) >= 2 and cleaned.startswith('"') and cleaned.endswith('"'):
        cleaned = cleaned[1:-1]

    if cleaned.isdigit():
        return int(cleaned)

    prefix = f"{entity}-{entity_id}-v"
    if cleaned.startswith(prefix) and cleaned[len(prefix) :].isdigit():
        return int(cleaned[len(prefix) :])

    return None


def check_concurrency(
    request,
    entity: str,
    instance: Any,
    body_version: int | None = None,
) -> None:
    """Enforces optimistic concurrency if If-Match header or body version is supplied."""
    current_version = int(instance.version)
    if_match = (request.headers.get("If-Match") or "").strip()

    if if_match and if_match != "*":
        parsed = _parse_if_match_version(if_match, entity, instance.id)
        if parsed is None or parsed != current_version:
            raise DomainError(
                code="TS_STATE_CONFLICT",
                message="Resource version conflict detected via If-Match header. Refresh and try again.",
                status_code=409,
            )

    if body_version is not None and int(body_version) != current_version:
        raise DomainError(
            code="TS_STATE_CONFLICT",
            message="Resource version conflict detected. Refresh and try again.",
            status_code=409,
        )
