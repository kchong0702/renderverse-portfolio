import os
from collections.abc import Callable, Sequence
from typing import Any, override

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.utils.function_calling import convert_to_openai_tool
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
from pydantic import Field

from src.core.config import Settings
from src.infrastructure.observability import instrumentation, metrics, tracing


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


class ScriptedChatModel(BaseChatModel):
    replies: list[AIMessage]
    requests: list[list[BaseMessage]] = Field(default_factory=list)
    offered_tools: list[set[str]] = Field(default_factory=list)
    tool_descriptions: list[dict[str, str]] = Field(default_factory=list)
    model_name: str = "glm-5.3"
    provider: str = "openai"

    @property
    @override
    def _llm_type(self) -> str:
        return "scripted"

    @override
    def _get_ls_params(self, stop: list[str] | None = None, **kwargs: Any) -> Any:
        return {"ls_provider": self.provider, "ls_model_name": self.model_name}

    @override
    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Any:
        functions = [convert_to_openai_tool(tool)["function"] for tool in tools]
        self.offered_tools.append({function["name"] for function in functions})
        self.tool_descriptions.append(
            {
                function["name"]: function.get("description", "")
                for function in functions
            }
        )
        return self

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        self.requests.append(messages)
        reply = self.replies[min(len(self.requests), len(self.replies)) - 1]
        return ChatResult(generations=[ChatGeneration(message=reply)])


def pytest_configure(config: pytest.Config) -> None:
    os.environ["EZCAREER_HARNESS_OBSERVABILITY__TRACING_ENABLED"] = "false"
    os.environ["EZCAREER_HARNESS_OBSERVABILITY__METRICS_ENABLED"] = "false"


@pytest.fixture
def isolate_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the developer's .env and shell EZCAREER_HARNESS_* overrides out of tests"""
    for key in list(os.environ):
        if key.startswith("EZCAREER_HARNESS_"):
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
