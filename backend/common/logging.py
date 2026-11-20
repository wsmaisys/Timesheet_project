"""Request-scoped correlation ID context and logging filter."""

import contextvars
import logging

_request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


def get_request_id() -> str:
    return _request_id_var.get()


def set_request_id(request_id: str) -> contextvars.Token[str]:
    return _request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token[str]) -> None:
    _request_id_var.reset(token)


class RequestIDFilter(logging.Filter):
    """Injects the current request_id into every structured log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True
