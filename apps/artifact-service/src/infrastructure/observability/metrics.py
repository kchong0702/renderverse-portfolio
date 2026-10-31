from __future__ import annotations

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

from src.core.config import Settings, get_settings
from src.infrastructure.observability.otlp import (
    build_endpoint,
    build_resource,
    parse_headers,
)

_configured: bool = False
_provider: MeterProvider | None = None


def configure_metrics(settings: Settings | None = None, *, force: bool = False) -> None:
    """Configure an OTLP meter provider from Settings.

    Idempotent: a second call without ``force=True`` is a no-op so library
    code can call this defensively. Pass ``force=True`` to reconfigure
    (e.g. after settings reload in tests). When
    ``observability.metrics_enabled`` is False this is a no-op and the
    OpenTelemetry API default no-op meter remains in effect.
    """
    global _configured, _provider
    if _configured and not force:
        return

    settings = settings or get_settings()
    obs = settings.observability

    if not obs.metrics_enabled:
        _configured = True
        return

    exporter = OTLPMetricExporter(
        endpoint=build_endpoint(obs, "metrics"),
        headers=parse_headers(obs),
    )
    reader = PeriodicExportingMetricReader(
        exporter, export_interval_millis=obs.metrics_export_interval_ms
    )
    provider = MeterProvider(resource=build_resource(settings), metric_readers=[reader])
    metrics.set_meter_provider(provider)

    _provider = provider
    _configured = True


def get_meter(name: str | None = None) -> metrics.Meter:
    """Get meter by name, create one if not exist"""
    if not _configured:
        configure_metrics()
    return metrics.get_meter(name) if name else metrics.get_meter(__name__)


def shutdown_metrics() -> None:
    """Flush pending metrics and shut down the meter provider, if one was configured."""
    global _provider
    if _provider is None:
        return
    _provider.shutdown()
    _provider = None


__all__ = ["configure_metrics", "get_meter", "shutdown_metrics"]
