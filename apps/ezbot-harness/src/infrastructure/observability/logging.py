from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from src.core.config import ObservabilitySettings, Settings, get_settings

_configured: bool = False


def _add_service_context(service_name: str, env: str) -> Processor:
    """Add service name to trace context."""

    def processor(_: Any, __: str, event_dict: EventDict) -> EventDict:
        event_dict.setdefault("service", service_name)
        event_dict.setdefault("env", env)
        return event_dict

    return processor


def _truncate_longtext(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Truncate long payload text in logs"""

    def _truncate(data: Any) -> Any:
        if isinstance(data, str):
            if len(data) > 1000:
                return f"<TRUNCATED_LARGE_STRING | len: {len(data)}>"
            return data
        elif isinstance(data, dict):
            return {k: _truncate(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [_truncate(v) for v in data]
        return data

    for key, value in event_dict.items():
        event_dict[key] = _truncate(value)

    return event_dict


def _build_shared_processors(obs: ObservabilitySettings, env: str) -> list[Processor]:
    """Build shared processors for structlog and stdlib"""
    return [
        structlog.contextvars.merge_contextvars,
        _add_service_context(obs.service_name, env),
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        # Before format_exc_info so long tracebacks are never truncated
        _truncate_longtext,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]


def _build_renderer(log_format: str) -> Processor:
    """Build log renderer, either in json or console format"""
    if log_format == "json":
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer(colors=True, force_colors=True)


def configure_logging(settings: Settings | None = None, *, force: bool = False) -> None:
    """Configure structlog and stdlib logging.

    Idempotent: a second call without ``force=True`` is a no-op so library
    code can call this defensively. Pass ``force=True`` to reconfigure.
    """
    global _configured
    if _configured and not force:
        return

    settings = settings or get_settings()
    obs = settings.observability
    shared = _build_shared_processors(obs, settings.app.env)
    renderer = _build_renderer(obs.log_format)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(obs.log_level)

    _configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Centralize location to get structlog logger.

    Accessing logger through this function as best practice.
    This function ensure loggers are configured providing
    consistent format to application.
    """
    if not _configured:
        configure_logging()
    return structlog.stdlib.get_logger(name) if name else structlog.stdlib.get_logger()


__all__ = ["configure_logging", "get_logger"]
