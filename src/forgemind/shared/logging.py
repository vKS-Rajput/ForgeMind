"""Structured logging configuration for ForgeMind.

Uses structlog for machine-readable, context-rich logging.
Automatically switches between:
- Console renderer (colorful, human-readable) for local development
- JSON renderer (machine-parseable) for production

Usage:
    from forgemind.shared.logging import configure_logging, get_logger

    configure_logging(log_level="DEBUG", log_format="console")
    logger = get_logger(__name__)
    logger.info("entity_extracted", entity_name="P-101", confidence=0.95)

Bounded Context: Shared
Layer: Infrastructure
Dependencies: structlog
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format: Output format. "json" for production, "console" for development.
            If "console" or if stderr is a TTY, uses colorful console output.
    """
    # Shared processors for both renderers
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Select renderer based on format / TTY detection
    renderer: Any
    if log_format == "console" or sys.stderr.isatty():
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelNamesMapping().get(log_level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound to the given module name.

    Args:
        name: Module name, typically __name__.

    Returns:
        A bound structured logger.
    """
    return structlog.get_logger(name)  # type: ignore[no-any-return]
