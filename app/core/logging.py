"""Structured logging configuration with request ID support."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from app.core.config import settings

# Context variable to store request ID across async boundaries
request_id_var: ContextVar[str] = ContextVar("request_id", default="unknown")


class RequestIdFilter(logging.Filter):
    """Injects request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str | None = None) -> str:
    """Set (or generate) the request ID in context."""
    if request_id is None:
        request_id = str(uuid.uuid4())
    request_id_var.set(request_id)
    return request_id


def setup_logging() -> logging.Logger:
    """Configure structured logging for the application."""
    logger = logging.getLogger("url_audit")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers = []

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.addFilter(RequestIdFilter())

    if settings.environment == "production":
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | request_id=%(request_id)s | %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(request_id)s | %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


logger = setup_logging()
