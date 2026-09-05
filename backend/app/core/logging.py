"""
Structured logging with structlog.

Provides a consistent, JSON-friendly log format for production
and a human-readable format for development.
"""

from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(*, debug: bool = False) -> None:
    """Configure structlog + stdlib logging for the application."""

    log_level = logging.DEBUG if debug else logging.INFO

    # Shared structlog processors
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ExtraAdder(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        # Human-readable coloured output for local dev
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=sys.stdout.isatty()
        )
    else:
        # JSON output for production / container logs
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Quieten noisy libraries
    for name in ("uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a bound logger instance."""
    return structlog.get_logger(name)
