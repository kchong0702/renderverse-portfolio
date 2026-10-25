from typing import TypedDict

import pytest
from langgraph.graph import END, START, StateGraph
from opentelemetry import metrics as metrics_api
from opentelemetry import trace as trace_api

from src.core.config import ObservabilitySettings
from src.infrastructure.observability import metrics, tracing
from src.infrastructure.observability.instrumentation import instrument
from src.infrastructure.observability.otlp import build_endpoint, parse_headers

pytestmark = pytest.mark.usefixtures("isolate_env")

ENDPOINT = "http://collector:4318"


@pytest.mark.parametrize(
    ("endpoint", "signal", "expected"),
    [
        ("http://collector:4318", "traces", "http://collector:4318/v1/traces"),
        ("http://collector:4318/", "metrics", "http://collector:4318/v1/metrics"),
        (
            "http://collector:4318/v1/metrics",
            "metrics",
            "http://collector:4318/v1/metrics",
        ),
    ],
)
def test_build_endpoint(endpoint, signal, expected):
    obs = ObservabilitySettings(otlp_endpoint=endpoint)

    assert build_endpoint(obs, signal) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, None),
        ("  ", None),
        ("Authorization=Basic YWJj==", {"Authorization": "Basic YWJj=="}),
        ("X-Org = acme, X-Env=dev,", {"X-Org": "acme", "X-Env": "dev"}),
    ],
)
def test_parse_headers(raw, expected):
    obs = ObservabilitySettings(otlp_headers=raw)

    assert parse_headers(obs) == expected


def test_disabled_signals_keep_noop_providers(
    make_settings, span_exporters, metric_exporters
):
    settings = make_settings()

    tracing.configure_tracing(settings)
    metrics.configure_metrics(settings)

    assert span_exporters == [] and metric_exporters == []
    assert isinstance(trace_api.get_tracer_provider(), trace_api.ProxyTracerProvider)
    assert isinstance(
        metrics_api.get_meter_provider(), metrics_api._internal._ProxyMeterProvider
    )


def test_tracing_exports_spans(make_settings, span_exporters):
    settings = make_settings(
        tracing_enabled=True,
        otlp_endpoint=ENDPOINT,
        otlp_headers="Authorization=Bearer token",
    )
    tracing.configure_tracing(settings)
    tracing.configure_tracing(settings)  # idempotent

    with tracing.get_tracer("test").start_as_current_span("hello"):
        pass
    tracing.shutdown_tracing()

    [exporter] = span_exporters
    assert exporter.kwargs == {
        "endpoint": f"{ENDPOINT}/v1/traces",
        "headers": {"Authorization": "Bearer token"},
    }
    [span] = exporter.spans
    assert span.name == "hello"
    assert span.resource.attributes["service.name"] == "ezbot"
    assert span.resource.attributes["service.version"] == "0.1.0"
    assert span.resource.attributes["deployment.environment"] == "dev"


def test_metrics_exports_on_shutdown(make_settings, metric_exporters):
    settings = make_settings(metrics_enabled=True, otlp_endpoint=ENDPOINT)
    metrics.configure_metrics(settings)
    metrics.configure_metrics(settings)  # idempotent

    counter = metrics.get_meter("test").create_counter("ezbot.test.requests")
    counter.add(2)
    counter.add(1)
    metrics.shutdown_metrics()

    [exporter] = metric_exporters
    assert exporter.kwargs == {"endpoint": f"{ENDPOINT}/v1/metrics", "headers": None}
    exported = {
        metric.name: (resource_metrics.resource, metric)
        for batch in exporter.batches
        for resource_metrics in batch.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
    }
    resource, metric = exported["ezbot.test.requests"]
    assert sum(point.value for point in metric.data.data_points) == 3
    assert resource.attributes["service.name"] == "ezbot"


class _State(TypedDict):
    count: int


def test_langchain_instrumentation_traces_langgraph(make_settings, span_exporters):
    settings = make_settings(
        tracing_enabled=True, otlp_endpoint=ENDPOINT, instrumentations=["langchain"]
    )
    instrument(settings)

    builder = StateGraph(_State)
    builder.add_node("increment", lambda state: {"count": state["count"] + 1})
    builder.add_edge(START, "increment")
    builder.add_edge("increment", END)
    assert builder.compile().invoke({"count": 1}) == {"count": 2}
    tracing.shutdown_tracing()

    [exporter] = span_exporters
    names = {span.name for span in exporter.spans}
    assert "increment" in names
    assert all("openinference.span.kind" in span.attributes for span in exporter.spans)
