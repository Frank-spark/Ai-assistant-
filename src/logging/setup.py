"""Logging and monitoring setup for Reflex Executive Assistant."""

import logging
import sys
from typing import Any, Dict, Optional
from contextvars import ContextVar
import structlog
from structlog.stdlib import LoggerFactory
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from prometheus_client.registry import CollectorRegistry

from ..config import get_settings

# Context variables for request tracking
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "reflex_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status_code"]
)

REQUEST_DURATION = Histogram(
    "reflex_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint"]
)

ACTIVE_REQUESTS = Gauge(
    "reflex_active_requests",
    "Number of active requests"
)

WEBHOOK_COUNT = Counter(
    "reflex_webhook_total",
    "Total number of webhook calls",
    ["source", "status"]
)

AI_MODEL_CALLS = Counter(
    "reflex_ai_model_calls_total",
    "Total number of AI model calls",
    ["model", "status"]
)

VECTOR_DB_OPERATIONS = Counter(
    "reflex_vector_db_operations_total",
    "Total number of vector database operations",
    ["operation", "status"]
)


def setup_logging() -> None:
    """Setup structured logging with structlog."""
    settings = get_settings()
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            add_context_data,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper())
    )


def add_context_data(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add request context data to log entries."""
    # Add request tracking context
    if request_id_var.get():
        event_dict["request_id"] = request_id_var.get()
    if user_id_var.get():
        event_dict["user_id"] = user_id_var.get()
    if correlation_id_var.get():
        event_dict["correlation_id"] = correlation_id_var.get()
    
    # Add service information
    event_dict["service"] = "reflex-executive-assistant"
    event_dict["version"] = "0.1.0"
    
    return event_dict


def setup_opentelemetry() -> None:
    """Setup OpenTelemetry tracing."""
    settings = get_settings()
    
    # Create tracer provider
    resource = Resource.create({"service.name": "reflex-executive-assistant"})
    provider = TracerProvider(resource=resource)
    
    # Add console exporter for development
    if settings.is_development():
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(
            trace.BatchSpanProcessor(console_exporter)
        )
    
    # Add OTLP exporter if endpoint is configured
    if settings.otel_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
        provider.add_span_processor(
            trace.BatchSpanProcessor(otlp_exporter)
        )
    
    # Set global tracer provider
    trace.set_tracer_provider(provider)
    
    return provider


def setup_prometheus() -> None:
    """Setup Prometheus metrics server."""
    settings = get_settings()
    
    if settings.enable_metrics:
        try:
            start_http_server(settings.prometheus_port)
            structlog.get_logger().info(
                "Prometheus metrics server started",
                port=settings.prometheus_port
            )
        except Exception as e:
            structlog.get_logger().error(
                "Failed to start Prometheus metrics server",
                error=str(e),
                port=settings.prometheus_port
            )


def instrument_fastapi(app: Any) -> None:
    """Instrument FastAPI application with OpenTelemetry."""
    try:
        FastAPIInstrumentor.instrument_app(app)
        structlog.get_logger().info("FastAPI instrumented with OpenTelemetry")
    except Exception as e:
        structlog.get_logger().error(
            "Failed to instrument FastAPI with OpenTelemetry",
            error=str(e)
        )


def instrument_database() -> None:
    """Instrument database connections with OpenTelemetry."""
    try:
        Psycopg2Instrumentor().instrument()
        structlog.get_logger().info("PostgreSQL instrumented with OpenTelemetry")
    except Exception as e:
        structlog.get_logger().error(
            "Failed to instrument PostgreSQL with OpenTelemetry",
            error=str(e)
        )


def instrument_redis() -> None:
    """Instrument Redis connections with OpenTelemetry."""
    try:
        RedisInstrumentor().instrument()
        structlog.get_logger().info("Redis instrumented with OpenTelemetry")
    except Exception as e:
        structlog.get_logger().error(
            "Failed to instrument Redis with OpenTelemetry",
            error=str(e)
        )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def set_request_context(
    request_id: str,
    user_id: Optional[str] = None,
    correlation_id: Optional[str] = None
) -> None:
    """Set request context for logging."""
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if correlation_id:
        correlation_id_var.set(correlation_id)


def clear_request_context() -> None:
    """Clear request context."""
    request_id_var.set(None)
    user_id_var.set(None)
    correlation_id_var.set(None)


def log_request_start(method: str, endpoint: str) -> None:
    """Log the start of a request and increment active requests gauge."""
    ACTIVE_REQUESTS.inc()
    get_logger("http").info(
        "Request started",
        method=method,
        endpoint=endpoint
    )


def log_request_end(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float
) -> None:
    """Log the end of a request and update metrics."""
    ACTIVE_REQUESTS.dec()
    REQUEST_COUNT.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
    get_logger("http").info(
        "Request completed",
        method=method,
        endpoint=endpoint,
        status_code=status_code,
        duration=duration
    )


def log_webhook_call(source: str, status: str, details: Optional[Dict[str, Any]] = None) -> None:
    """Log webhook calls and update metrics."""
    WEBHOOK_COUNT.labels(source=source, status=status).inc()
    
    log_data = {
        "webhook_source": source,
        "status": status
    }
    if details:
        log_data.update(details)
    
    get_logger("webhook").info("Webhook call", **log_data)


def log_ai_model_call(
    model: str,
    status: str,
    duration: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log AI model calls and update metrics."""
    AI_MODEL_CALLS.labels(model=model, status=status).inc()
    
    log_data = {
        "model": model,
        "status": status
    }
    if duration:
        log_data["duration"] = duration
    if details:
        log_data.update(details)
    
    get_logger("ai").info("AI model call", **log_data)


def log_vector_db_operation(
    operation: str,
    status: str,
    duration: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log vector database operations and update metrics."""
    VECTOR_DB_OPERATIONS.labels(operation=operation, status=status).inc()
    
    log_data = {
        "operation": operation,
        "status": status
    }
    if duration:
        log_data["duration"] = duration
    if details:
        log_data.update(details)
    
    get_logger("vector_db").info("Vector DB operation", **log_data) 