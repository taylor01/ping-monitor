"""
Structured logging configuration with correlation tracking
"""

import structlog
import logging
import uuid
from contextvars import ContextVar
from typing import Any, Dict

# Context variable for correlation ID
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


def generate_correlation_id() -> str:
    """Generate a new correlation ID"""
    return str(uuid.uuid4())


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context"""
    correlation_id_var.set(correlation_id)


def get_correlation_id() -> str:
    """Get the current correlation ID"""
    return correlation_id_var.get()


def add_correlation_id(
    logger: Any, method_name: str, event_dict: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Processor to add correlation ID to all log entries
    """
    correlation_id = correlation_id_var.get()
    if correlation_id:
        event_dict["correlation_id"] = correlation_id
    return event_dict


def configure_logging() -> None:
    """
    Configure structlog with JSON output and correlation tracking
    """
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.INFO,
    )

    # Configure structlog processors
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            add_correlation_id,  # Add correlation ID
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),  # JSON output
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance
    """
    return structlog.get_logger(name)
