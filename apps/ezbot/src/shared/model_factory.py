from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult


class EchoChatModel(BaseChatModel):
    """Placeholder model that streams the latest message back word by word.

    Stands in for a real provider until one is chosen, so streaming and
    cancellation can be exercised end to end.
    """

    token_delay_s: float = 0.05
    """Delay between streamed words, mimicking LLM token latency"""

    @property
    def _llm_type(self) -> str:
        return "echo"

    @staticmethod
    def _reply(messages: list[BaseMessage]) -> str:
        return f"Echo: {messages[-1].text}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        message = AIMessage(content=self._reply(messages))
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        for index, word in enumerate(self._reply(messages).split(" ")):
            await asyncio.sleep(self.token_delay_s)
            token = word if index == 0 else f" {word}"
            yield ChatGenerationChunk(message=AIMessageChunk(content=token))


def create_model() -> BaseChatModel:
    """Create the chat model backing Ezbot"""
    return EchoChatModel()


__all__ = ["EchoChatModel", "create_model"]
