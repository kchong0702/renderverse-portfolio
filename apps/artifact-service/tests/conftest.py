import base64
import hashlib
import os
from collections.abc import Callable, Sequence
from typing import Any, override

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
from src.infrastructure.observability import metrics, tracing


class FakeSpanExporter(SpanExporter):
    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.spans: list[ReadableSpan] = []

    @override
    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        self.spans.extend(spans)
        return SpanExportResult.SUCCESS

    @override
    def shutdown(self) -> None:
        pass


class FakeMetricExporter(MetricExporter):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__()
        self.kwargs = kwargs
        self.batches: list[MetricsData] = []

    @override
    def export(
        self, metrics_data: MetricsData, timeout_millis: float = 10_000, **kwargs: Any
    ) -> MetricExportResult:
        self.batches.append(metrics_data)
        return MetricExportResult.SUCCESS

    @override
    def force_flush(self, timeout_millis: float = 10_000) -> bool:
        return True

    @override
    def shutdown(self, timeout_millis: float = 30_000, **kwargs: Any) -> None:
        pass


def pytest_configure(config: pytest.Config) -> None:
    # Settings cached by app modules must never export telemetry from tests,
    # whatever .env or config.toml enable
    os.environ["ARTIFACT_SERVICE_OBSERVABILITY__TRACING_ENABLED"] = "false"
    os.environ["ARTIFACT_SERVICE_OBSERVABILITY__METRICS_ENABLED"] = "false"


@pytest.fixture
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's .env and shell ARTIFACT_SERVICE_* overrides out of tests"""
    for key in list(os.environ):
        if key.startswith("ARTIFACT_SERVICE_"):
            monkeypatch.delenv(key)


@pytest.fixture(autouse=True)
def _reset_observability():
    yield
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


# 1x1 transparent PNG
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
PNG_SHA = hashlib.sha256(PNG).hexdigest()

TEMPLATE_HTML = """
<h1 data-field="{{header.name.path}}">{{header.name.text}}</h1>
{{#header.photo}}<img class="photo" src="asset:{{header.photo}}" alt="">{{/header.photo}}
{{#sections}}<section>
  {{#heading}}<h2 data-field="{{path}}">{{text}}</h2>{{/heading}}
  {{#text}}<p data-field="{{path}}">{{text}}</p>{{/text}}
  {{#items}}<div class="item">
    {{#title}}<h3 data-field="{{path}}">{{text}}</h3>{{/title}}
    <ul>{{#bullets}}<li data-field="{{text.path}}">{{text.text}}</li>{{/bullets}}</ul>
    {{#links}}<a href="{{url.text}}" data-field="{{url.path}}">{{url.text}}</a>{{/links}}
  </div>{{/items}}
  {{#is_skills}}<p>{{#tags}}<span data-field="{{text.path}}">{{text.text}}</span> {{/tags}}</p>{{/is_skills}}
</section>{{/sections}}
"""


def value(text: str) -> dict[str, Any]:
    return {"text": text, "src": ["p1.s1"]}


@pytest.fixture
def document_data() -> dict[str, Any]:
    """A one-page résumé whose template shows every Value it holds"""
    return {
        "kind": "resume",
        "content": {
            "header": {"name": value("Ada Lovelace"), "photo": PNG_SHA},
            "sections": [
                {"id": "sum", "kind": "summary", "text": value("Writes programs.")},
                {
                    "id": "exp",
                    "kind": "experience",
                    "heading": value("Experience"),
                    "items": [
                        {
                            "id": "it_1",
                            "title": value("Programmer"),
                            "bullets": [
                                {
                                    "id": "b_1",
                                    "text": value("Wrote the first algorithm"),
                                },
                                {"id": "b_2", "text": value("Annotated the notes")},
                            ],
                            "links": [
                                {"id": "l_1", "url": value("https://github.com/ada")}
                            ],
                        }
                    ],
                },
                {
                    "id": "sk",
                    "kind": "skills",
                    "heading": value("Skills"),
                    "tags": [
                        {"id": "t_1", "text": value("Mathematics")},
                        {"id": "t_2", "text": value("Punch cards")},
                    ],
                },
            ],
        },
        "template": {
            "html": TEMPLATE_HTML,
            "css": "body { font: 12px/1.4 sans-serif; } .photo { width: 40px; }",
            "tokens": {
                "--page-margin-top": "16mm",
                "--page-margin-right": "16mm",
                "--page-margin-bottom": "16mm",
                "--page-margin-left": "16mm",
                "--accent": "#1f3a5f",
            },
        },
        "assets": {PNG_SHA: {"media_type": "image/png", "uri": "assets/photo.png"}},
    }
