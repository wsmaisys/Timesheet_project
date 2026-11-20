"""Standardized ErrorEnvelope exception handling (SRS §10)."""

import logging
from typing import Any

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError
from django.http import Http404, JsonResponse
from rest_framework import exceptions as drf_exceptions
from rest_framework.response import Response

from .logging import get_request_id

logger = logging.getLogger(__name__)


class DomainError(Exception):
    """Structured domain exception mapped to the normative API error envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []


def build_error_payload(
    code: str,
    message: str,
    details: list[dict[str, str]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    error_obj: dict[str, Any] = {
        "code": code,
        "message": message,
        "request_id": request_id or get_request_id(),
    }
    if details:
        error_obj["details"] = details
    return {"error": error_obj}


def _flatten_drf_errors(detail: Any, prefix: str = "") -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if isinstance(detail, dict):
        for key, value in detail.items():
            next_prefix = f"{prefix}.{key}" if prefix else str(key)
            items.extend(_flatten_drf_errors(value, next_prefix))
    elif isinstance(detail, list):
        for entry in detail:
            if isinstance(entry, (dict, list)):
                items.extend(_flatten_drf_errors(entry, prefix))
            else:
                items.append({"field": prefix or "non_field_errors", "issue": str(entry)})
    elif detail is not None:
        items.append({"field": prefix or "non_field_errors", "issue": str(detail)})
    return items


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    request = context.get("request")
    request_id = getattr(request, "request_id", None) or get_request_id()

    if isinstance(exc, DomainError):
        return Response(
            build_error_payload(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
            status=exc.status_code,
        )

    if isinstance(exc, (Http404, drf_exceptions.NotFound)):
        return Response(
            build_error_payload(
                code="RESOURCE_NOT_FOUND",
                message="The requested resource was not found.",
                request_id=request_id,
            ),
            status=404,
        )

    if isinstance(exc, (DjangoPermissionDenied, drf_exceptions.PermissionDenied)):
        return Response(
            build_error_payload(
                code="AUTH_FORBIDDEN",
                message=str(getattr(exc, "detail", None) or "You do not have permission to perform this action."),
                request_id=request_id,
            ),
            status=403,
        )

    if isinstance(exc, drf_exceptions.NotAuthenticated):
        return Response(
            build_error_payload(
                code="AUTH_INVALID_TOKEN",
                message="Authentication credentials were not provided.",
                request_id=request_id,
            ),
            status=401,
        )

    if isinstance(exc, drf_exceptions.AuthenticationFailed):
        detail_code = getattr(exc, "default_code", "authentication_failed")
        code_str = "AUTH_INVALID_TOKEN"
        if isinstance(exc.detail, dict) and "code" in exc.detail:
            raw_code = str(exc.detail.get("code", ""))
            if raw_code == "AUTH_ACCOUNT_DISABLED":
                code_str = "AUTH_ACCOUNT_DISABLED"
            elif raw_code == "AUTH_INVALID_CREDENTIALS":
                code_str = "AUTH_INVALID_CREDENTIALS"
        elif detail_code == "authentication_failed":
            code_str = "AUTH_INVALID_TOKEN"

        return Response(
            build_error_payload(
                code=code_str,
                message="Authentication credentials are invalid or expired.",
                request_id=request_id,
            ),
            status=401,
        )

    if isinstance(exc, drf_exceptions.Throttled):
        response = Response(
            build_error_payload(
                code="RATE_LIMIT_EXCEEDED",
                message="Too many requests. Please retry later.",
                request_id=request_id,
            ),
            status=429,
        )
        if exc.wait is not None:
            response["Retry-After"] = str(int(exc.wait))
        return response

    if isinstance(exc, drf_exceptions.MethodNotAllowed):
        return Response(
            build_error_payload(
                code="METHOD_NOT_ALLOWED",
                message=f"Method {exc.args[0] if exc.args else ''} is not allowed on this endpoint.",
                request_id=request_id,
            ),
            status=405,
        )

    if isinstance(exc, DjangoValidationError):
        detail = getattr(exc, "message_dict", None) or getattr(exc, "messages", None) or str(exc)
        details = _flatten_drf_errors(detail)
        message = details[0]["issue"] if details else "Invalid input parameter."
        return Response(
            build_error_payload(
                code="VALIDATION_ERROR",
                message=message,
                details=details,
                request_id=request_id,
            ),
            status=400,
        )

    if isinstance(exc, (drf_exceptions.ValidationError, drf_exceptions.ParseError)):
        details = _flatten_drf_errors(exc.detail)
        message = details[0]["issue"] if details else "Request validation failed."
        return Response(
            build_error_payload(
                code="VALIDATION_ERROR",
                message=message,
                details=details,
                request_id=request_id,
            ),
            status=400,
        )

    from rest_framework.views import exception_handler as drf_default_exception_handler

    drf_response = drf_default_exception_handler(exc, context)
    if drf_response is not None:
        return Response(
            build_error_payload(
                code="VALIDATION_ERROR" if drf_response.status_code < 500 else "INTERNAL_ERROR",
                message=str(drf_response.data) if drf_response.status_code < 500 else "Internal server error.",
                request_id=request_id,
            ),
            status=drf_response.status_code,
        )

    if isinstance(exc, DatabaseError):
        logger.exception("Database error while handling API request", exc_info=exc)
        return Response(
            build_error_payload(
                code="INTERNAL_ERROR",
                message="A database error occurred while processing the request.",
                request_id=request_id,
            ),
            status=500,
        )

    logger.exception("Unhandled exception while handling API request", exc_info=exc)
    return Response(
        build_error_payload(
            code="INTERNAL_ERROR",
            message="An unexpected internal server error occurred.",
            request_id=request_id,
        ),
        status=500,
    )


def json_404_handler(request, exception=None):
    return JsonResponse(
        build_error_payload(
            code="RESOURCE_NOT_FOUND",
            message="The requested endpoint or resource was not found.",
            request_id=getattr(request, "request_id", None),
        ),
        status=404,
    )


def json_500_handler(request):
    return JsonResponse(
        build_error_payload(
            code="INTERNAL_ERROR",
            message="An unexpected internal server error occurred.",
            request_id=getattr(request, "request_id", None),
        ),
        status=500,
    )
