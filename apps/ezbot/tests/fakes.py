from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from src.core.agent.classifier.base import IntentClassifier
from src.shared.schemas.intent import Intent


class EchoChatModel(BaseChatModel):
    """Streams the latest message back word by word, recording every call"""

    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "echo"

    @staticmethod
    def _reply(messages: list[BaseMessage]) -> str:
        return f"Echo: {messages[-1].text}"

    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        self.calls.append(list(messages))
        message = AIMessage(content=self._reply(messages))
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _astream(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        self.calls.append(list(messages))
        for index, word in enumerate(self._reply(messages).split(" ")):
            await asyncio.sleep(0)
            token = word if index == 0 else f" {word}"
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))


class ToolCallingChatModel(BaseChatModel):
    """Calls `tool_name` once per user message, then answers with its result"""

    tool_name: str
    calls: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "tool-calling"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> ToolCallingChatModel:
        return self

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        self.calls.append(list(messages))
        if isinstance(messages[-1], ToolMessage):
            return AIMessage(content=f"Found: {messages[-1].text}")
        call_id = f"call-{len(self.calls)}"
        return AIMessage(
            content="", tool_calls=[{"name": self.tool_name, "args": {}, "id": call_id}]
        )

    def _generate(
        self, messages: list[BaseMessage], *args: Any, **kwargs: Any
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._reply(messages))])


class FailingChatModel(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "failing"

    def _generate(self, *args: Any, **kwargs: Any) -> ChatResult:
        raise RuntimeError("provider unavailable")

    async def _astream(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        raise RuntimeError("provider unavailable")
        yield  # pragma: no cover


class BlockingChatModel(BaseChatModel):
    """Streams one token, then blocks until cancelled"""

    cancelled: asyncio.Event
    started: asyncio.Event

    @property
    def _llm_type(self) -> str:
        return "blocking"

    def _generate(self, *args: Any, **kwargs: Any) -> ChatResult:
        raise NotImplementedError

    async def _astream(
        self, *args: Any, **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        yield ChatGenerationChunk(message=AIMessageChunk(content="thinking"))
        self.started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.cancelled.set()
            raise


class FakeIntentClassifier(IntentClassifier):
    """Returns a fixed intent and records the conversations it was asked about"""

    def __init__(self, intent: Intent | None = None, delay_s: float = 0):
        self.intent = intent
        self.delay_s = delay_s
        self.seen: list[Sequence[BaseMessage]] = []
        self.cancelled = False
        self.closed = False

    async def classify(self, messages: Sequence[BaseMessage]) -> Intent | None:
        self.seen.append(list(messages))
        try:
            await asyncio.sleep(self.delay_s)
        except asyncio.CancelledError:
            self.cancelled = True
            raise
        return self.intent

    async def aclose(self) -> None:
        self.closed = True
