from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.core.config import Settings, get_settings
from src.infrastructure.observability.otlp import (
    build_endpoint,
    build_resource,
    parse_headers,
)

_configured: bool = False
_provider: TracerProvider | None = None


def configure_tracing(settings: Settings | None = None, *, force: bool = False) -> None:
    """Configure an OTLP tracer provider from Settings.

    Idempotent: a second call without ``force=True`` is a no-op so library
    code can call this defensively. Pass ``force=True`` to reconfigure
    (e.g. after settings reload in tests). When
    ``observability.tracing_enabled`` is False this is a no-op and the
    OpenTelemetry API default no-op tracer remains in effect.
    """
    global _configured, _provider
    if _configured and not force:
        return

    settings = settings or get_settings()
    obs = settings.observability

    if not obs.tracing_enabled:
        _configured = True
        return

    provider = TracerProvider(resource=build_resource(settings))
    exporter = OTLPSpanExporter(
        endpoint=build_endpoint(obs, "traces"),
        headers=parse_headers(obs),
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _provider = provider
    _configured = True


def get_tracer(name: str | None = None) -> trace.Tracer:
    """Get tracer by name, create one if not exist"""
    if not _configured:
        configure_tracing()
    return trace.get_tracer(name) if name else trace.get_tracer(__name__)


def shutdown_tracing() -> None:
    """Flush and shut down the tracer provider, if one was configured."""
    global _provider
    if _provider is None:
        return
    _provider.shutdown()
    _provider = None


__all__ = ["configure_tracing", "get_tracer", "shutdown_tracing"]
