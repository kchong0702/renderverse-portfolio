from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from src.core.config import (
    Instrumentation,
    Settings,
    TraceRedactionSettings,
    get_settings,
)
from src.infrastructure.observability.tracing import configure_tracing

if TYPE_CHECKING:
    from openinference.instrumentation import TraceConfig
    from opentelemetry.instrumentation.instrumentor import BaseInstrumentor

_configured: bool = False
_active: list[BaseInstrumentor] = []


def _build_trace_config(redaction: TraceRedactionSettings) -> TraceConfig:
    from openinference.instrumentation import TraceConfig

    return TraceConfig(
        hide_inputs=redaction.hide_inputs,
        hide_outputs=redaction.hide_outputs,
        hide_input_messages=redaction.hide_input_messages,
        hide_output_messages=redaction.hide_output_messages,
        hide_input_text=redaction.hide_input_text,
        hide_output_text=redaction.hide_output_text,
        hide_input_images=redaction.hide_input_images,
        hide_embedding_vectors=redaction.hide_embedding_vectors,
        hide_embeddings_text=redaction.hide_embeddings_text,
        hide_llm_invocation_parameters=redaction.hide_llm_invocation_parameters,
        base64_image_max_length=redaction.base64_image_max_length,
    )


def _instrument_langchain(config: TraceConfig) -> BaseInstrumentor:
    from openinference.instrumentation.langchain import LangChainInstrumentor

    instrumentor = LangChainInstrumentor()
    instrumentor.instrument(config=config)
    return instrumentor


_INSTRUMENTORS: dict[Instrumentation, Callable[[TraceConfig], BaseInstrumentor]] = {
    "langchain": _instrument_langchain,
}


def instrument(settings: Settings | None = None, *, force: bool = False) -> None:
    """Auto-instrument LLM frameworks via OpenInference.

    Idempotent: a second call without ``force=True`` is a no-op so library
    code can call this defensively. Pass ``force=True`` to re-apply (e.g.
    after settings reload in tests) — this uninstruments previously active
    instrumentors first. When ``observability.tracing_enabled`` is False or
    no instrumentations are configured this is a no-op. Calls
    ``configure_tracing`` first to ensure the OTLP provider is active
    before instrumentors hook into the callback system.
    """
    global _configured
    if _configured and not force:
        return
    if force:
        uninstrument()

    settings = settings or get_settings()
    obs = settings.observability

    if not obs.tracing_enabled or not obs.instrumentations:
        _configured = True
        return

    configure_tracing(settings)
    config = _build_trace_config(obs.trace_redaction)
    for name in obs.instrumentations:
        _active.append(_INSTRUMENTORS[name](config))

    _configured = True


def uninstrument() -> None:
    """Reverse all active OpenInference instrumentations."""
    global _configured
    while _active:
        _active.pop().uninstrument()
    _configured = False


__all__ = ["instrument", "uninstrument"]
