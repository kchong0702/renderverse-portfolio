import os
from collections.abc import Callable, Sequence
from typing import Any

import pytest
from opentelemetry import trace
from opentelemetry.metrics import _internal as metrics_api
from opentelemetry.sdk.metrics.export import (
    MetricExporter,
    MetricExportResult,
    MetricsData,
)
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.util._once import Once

from src.core.config import Settings
from src.infrastructure.observability import instrumentation, metrics, tracing


class FakeSpanExporter(SpanExporter):
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.spans: list[ReadableSpan] = []

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class FakeMetricExporter(MetricExporter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.kwargs = kwargs
        self.batches: list[MetricsData] = []

    def export(
        self, metrics_data: MetricsData, timeout_millis: float = 10_000, **kwargs: Any
    ) -> MetricExportResult:
        self.batches.append(metrics_data)
        return MetricExportResult.SUCCESS

    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    def shutdown(self, timeout_millis: float = 30_000, **kwargs: Any) -> None:
        pass


def pytest_configure(config: pytest.Config) -> None:
    # Settings cached by app modules must never export telemetry from tests,
    # whatever .env or config.toml enable
    os.environ["EZBOT_OBSERVABILITY__TRACING_ENABLED"] = "false"
    os.environ["EZBOT_OBSERVABILITY__METRICS_ENABLED"] = "false"


@pytest.fixture
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's .env and shell EZBOT_* overrides out of tests"""
    for key in list(os.environ):
        if key.startswith("EZBOT_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def _reset_observability():
    yield
    instrumentation.uninstrument()
    tracing.shutdown_tracing()
    metrics.shutdown_metrics()
    tracing._configured = False
    metrics._configured = False
    trace._TRACER_PROVIDER = None
    trace._TRACER_PROVIDER_SET_ONCE = Once()
    metrics_api._METER_PROVIDER = None
    metrics_api._METER_PROVIDER_SET_ONCE = Once()


@pytest.fixture
def make_settings() -> Callable[..., Settings]:
    """Settings from config.toml with explicit observability overrides, ignoring .env"""

    def factory(**observability: Any) -> Settings:
        defaults = {
            "tracing_enabled": False,
            "metrics_enabled": False,
            "instrumentations": [],
        }
        return Settings(_env_file=None, observability={**defaults, **observability})

    return factory


@pytest.fixture
def span_exporters(monkeypatch: pytest.MonkeyPatch) -> list[FakeSpanExporter]:
    created: list[FakeSpanExporter] = []

    def factory(**kwargs: Any) -> FakeSpanExporter:
        created.append(FakeSpanExporter(**kwargs))
        return created[-1]

    monkeypatch.setattr(tracing, "OTLPSpanExporter", factory)
    return created


@pytest.fixture
def metric_exporters(monkeypatch: pytest.MonkeyPatch) -> list[FakeMetricExporter]:
    created: list[FakeMetricExporter] = []

    def factory(**kwargs: Any) -> FakeMetricExporter:
        created.append(FakeMetricExporter(**kwargs))
        return created[-1]

    monkeypatch.setattr(metrics, "OTLPMetricExporter", factory)
    return created
