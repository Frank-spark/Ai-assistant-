"""Logging package for Reflex Executive Assistant."""

from .setup import (
    setup_logging,
    setup_opentelemetry,
    setup_prometheus,
    instrument_fastapi,
    instrument_database,
    instrument_redis,
    get_logger,
    set_request_context,
    clear_request_context,
    log_request_start,
    log_request_end,
    log_webhook_call,
    log_ai_model_call,
    log_vector_db_operation,
)

__all__ = [
    "setup_logging",
    "setup_opentelemetry",
    "setup_prometheus",
    "instrument_fastapi",
    "instrument_database",
    "instrument_redis",
    "get_logger",
    "set_request_context",
    "clear_request_context",
    "log_request_start",
    "log_request_end",
    "log_webhook_call",
    "log_ai_model_call",
    "log_vector_db_operation",
] 