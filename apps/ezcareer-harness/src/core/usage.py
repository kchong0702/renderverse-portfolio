from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any, override
from uuid import UUID

from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, LLMResult
from pydantic import BaseModel, ConfigDict

from src.core.config import get_settings


class Usage(BaseModel):
    model_config = ConfigDict(frozen=True, use_attribute_docstrings=True)

    provider: str
    """The model's family in [models], else LangChain's ls_provider"""

    model: str
    """The model the call asked for, as [models] names it"""

    agent: str
    """The configured agent whose graph made the call, else the executable"""

    node: str
    """The graph node that made the call"""

    input_tokens: int
    """Input tokens, cache reads and writes included"""

    output_tokens: int
    """Output tokens, reasoning included"""

    cache_read_tokens: int
    """Input tokens read from the prompt cache"""

    cache_write_tokens: int
    """Input tokens written to the prompt cache"""

    reasoning_tokens: int
    """Output tokens spent reasoning"""

    latency_ms: int
    """Time from the call's start to its end"""

    stop_reason: str | None
    """Why the provider stopped, such as end_turn or stop"""

    request_id: str | None
    """The provider's id for the response, such as resp_..."""


class UsageReporter(AsyncCallbackHandler):
    def __init__(
        self, report: Callable[[Usage], Awaitable[None]], executable: str
    ) -> None:
        """Reports each finished chat model call's usage through report"""
        self.report = report
        self.executable = executable
        self.chains: dict[UUID, tuple[str | None, UUID | None]] = {}
        self.calls: dict[UUID, tuple[float, str, dict[str, Any]]] = {}

    @override
    async def on_chain_start(
        self,
        serialized: dict[str, Any],
        inputs: dict[str, Any],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Notes the chain's name and parent, such as an agent's graph"""
        self.chains[run_id] = (kwargs.get("name"), parent_run_id)

    @override
    async def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Notes when the call started, and the nearest agent graph it runs in"""
        agents = {agent.name for agent in get_settings().agents}
        chain = parent_run_id
        while chain in self.chains and self.chains[chain][0] not in agents:
            chain = self.chains[chain][1]
        self.calls[run_id] = (
            monotonic(),
            self.chains[chain][0] if chain in self.chains else self.executable,
            metadata or {},
        )

    @override
    async def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Reports the call's usage, read from its final AIMessage"""
        started, agent, metadata = self.calls.pop(run_id)
        match response.generations[0][0]:
            case ChatGeneration(
                message=AIMessage(usage_metadata=usage, response_metadata=meta)
            ):
                model = metadata["ls_model_name"]
                tokens = usage or UsageMetadata(
                    input_tokens=0, output_tokens=0, total_tokens=0
                )
                inputs = tokens.get("input_token_details", {})
                outputs = tokens.get("output_token_details", {})
                await self.report(
                    Usage(
                        provider=next(
                            (
                                family
                                for family, names in get_settings().models.items()
                                if model in names
                            ),
                            metadata["ls_provider"],
                        ),
                        model=model,
                        agent=agent,
                        node=metadata["langgraph_node"],
                        input_tokens=tokens["input_tokens"],
                        output_tokens=tokens["output_tokens"],
                        cache_read_tokens=inputs.get("cache_read", 0),
                        cache_write_tokens=inputs.get("cache_creation", 0),
                        reasoning_tokens=outputs.get("reasoning", 0),
                        latency_ms=round((monotonic() - started) * 1000),
                        stop_reason=meta.get("stop_reason")
                        or meta.get("finish_reason")
                        or meta.get("status"),
                        request_id=meta.get("id"),
                    )
                )


__all__ = ["Usage", "UsageReporter"]
