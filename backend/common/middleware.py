"""Cross-cutting HTTP middleware for request tracing and security headers."""

import re
import uuid

from django.http import HttpRequest, HttpResponse

from .logging import reset_request_id, set_request_id

_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_.\-]{4,64}$")


class RequestIDMiddleware:
    """Propagates or generates a request correlation ID (`X-Request-ID`)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        incoming = (request.headers.get("X-Request-ID") or "").strip()
        if incoming and _SAFE_REQUEST_ID_RE.match(incoming):
            request_id = incoming
        else:
            request_id = f"req_{uuid.uuid4().hex[:16]}"

        request.request_id = request_id  # type: ignore[attr-defined]
        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)

        response["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware:
    """Adds baseline security response headers."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        response.setdefault("X-Content-Type-Options", "nosniff")
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        return response
