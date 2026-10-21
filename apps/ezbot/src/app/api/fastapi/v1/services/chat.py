from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph

from src.app.api.fastapi.v1.schemas.chat import Done, Error, Request, Token
from src.core.graph import RESPOND_NODE_NAME
from src.infrastructure.observability.logging import get_logger

_logger = get_logger(__name__)

_ROLE_TO_MESSAGE = {"user": HumanMessage, "assistant": AIMessage}


class ChatService:
    def __init__(self, graph: CompiledStateGraph):
        self._graph = graph

    @staticmethod
    def _to_messages(request: Request) -> list[BaseMessage]:
        """Convert the client conversation into LangChain messages, oldest first"""
        history = [_ROLE_TO_MESSAGE[m.role](content=m.content) for m in request.history]
        return [*history, HumanMessage(content=request.message)]

    async def stream(self, request: Request) -> AsyncIterator[ServerSentEvent]:
        """Stream the bot reply as `token` events followed by `done` or `error`.

        Cancelled when the client aborts the request, which cancels the graph run.
        """
        try:
            async for chunk, metadata in self._graph.astream(
                {"messages": self._to_messages(request)}, stream_mode="messages"
            ):
                if (
                    metadata.get("langgraph_node") == RESPOND_NODE_NAME
                    and isinstance(chunk, AIMessageChunk)
                    and chunk.text
                ):
                    yield ServerSentEvent(event="token", data=Token(content=chunk.text))

            yield ServerSentEvent(event="done", data=Done(finish_reason="stop"))
        except asyncio.CancelledError:
            _logger.info("Chat stream cancelled by client")
            raise
        except Exception:
            _logger.exception("Chat stream failed")
            yield ServerSentEvent(
                event="error",
                data=Error(
                    status_code=500,
                    code="CHAT_FAILED",
                    message="Ezbot failed to respond",
                ),
            )
