from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime

from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    ToolMessage,
)
from langgraph.graph.state import CompiledStateGraph

from src.app.api.fastapi.v1.schemas.chat import (
    OutputTextDelta,
    ResponseCancelled,
    ResponseCompleted,
    ResponseError,
    ResponseFailed,
    ResponseIntent,
)
from src.app.api.fastapi.v1.services.response import Response
from src.core.agent.graph import MODEL_NODE_NAME
from src.core.config import ChatSettings, StreamSettings
from src.infrastructure.observability.logging import get_logger
from src.shared.exceptions import ResponseInProgressError, ResponseNotFoundError
from src.shared.schemas.agent import EzbotContext
from src.shared.schemas.session import Session

_logger = get_logger(__name__)


def _last_turns(history: list[BaseMessage], max_turns: int) -> list[BaseMessage]:
    """The last `max_turns` turns. A turn starts at a user message and holds
    everything up to the next one: the response and any tool calls and results"""
    starts = [i for i, m in enumerate(history) if isinstance(m, HumanMessage)]
    if len(starts) <= max_turns:
        return history[starts[0] :] if starts else []
    return history[starts[-max_turns] :]


def _storable(messages: list[BaseMessage]) -> list[BaseMessage]:
    """A turn's messages fit to send back to a model: drops empty replies, and
    tool calls a stopped response never got results for along with their partial
    results, since providers reject both"""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    unanswered = {
        call["id"]
        for m in messages
        if isinstance(m, AIMessage)
        for call in m.tool_calls
        if call["id"] not in answered
    }
    dropped = {
        call["id"]
        for m in messages
        if isinstance(m, AIMessage) and any(c["id"] in unanswered for c in m.tool_calls)
        for call in m.tool_calls
    }
    return [
        m
        for m in messages
        if not (isinstance(m, AIMessage) and not m.text and not m.tool_calls)
        and not (
            isinstance(m, AIMessage) and any(c["id"] in dropped for c in m.tool_calls)
        )
        and not (isinstance(m, ToolMessage) and m.tool_call_id in dropped)
    ]


class ChatService:
    def __init__(
        self,
        graph: CompiledStateGraph,
        chat: ChatSettings,
        stream: StreamSettings,
        clock: Callable[[], float] | None = None,
    ):
        self._graph = graph
        self._chat = chat
        self._stream = stream
        self._clock = clock

    def _new_response(self) -> Response:
        if self._clock is None:
            return Response(self._stream.retry_ms)
        return Response(self._stream.retry_ms, clock=self._clock)

    def start(self, session: Session, message: str) -> Response:
        """Start the response to `message` in the background"""
        if session.response is not None and not session.response.done:
            raise ResponseInProgressError
        response = self._new_response()
        session.response = response
        response.task = asyncio.create_task(self._generate(session, response, message))
        return response

    def stop(self, session: Session) -> bool:
        """Stop the response in progress, if any"""
        if session.response is None or session.response.done:
            return False
        session.response.stop()
        return True

    def resume(
        self, session: Session, last_event_id: str | None
    ) -> tuple[Response, int]:
        """The session's response and the sequence number to resume after"""
        response = session.response
        if not isinstance(response, Response) or not response.resumable(
            self._stream.replay_ttl_s
        ):
            raise ResponseNotFoundError
        after = response.resume_point(last_event_id)
        if after is None:
            raise ResponseNotFoundError
        return response, after

    def _remember(
        self, session: Session, message: str, turn: list[BaseMessage]
    ) -> None:
        """Keep the user message and everything the agent added in response"""
        session.history.append(HumanMessage(content=message))
        session.history.extend(_storable(turn))
        session.history[:] = _last_turns(session.history, self._chat.max_turns)

    async def _generate(
        self, session: Session, response: Response, message: str
    ) -> None:
        """Stream the response as text deltas, then its intent and completion, or a failure"""
        context = [
            *_last_turns(session.history, self._chat.max_turns),
            HumanMessage(content=message),
        ]
        turn: list[BaseMessage] = []
        """Messages the agent added this turn, as of its last finished step"""
        partial: list[str] = []
        """Response text streamed since that step"""
        intent = None
        try:
            async for namespace, mode, data in self._graph.astream(
                {"messages": context},
                stream_mode=["messages", "values"],
                subgraphs=True,
                context=EzbotContext(today=datetime.now(UTC).date()),
            ):
                if mode == "values":
                    turn = data["messages"][len(context) :]
                    partial.clear()
                    if not namespace:
                        intent = data.get("intent")
                    continue
                chunk, metadata = data
                if (
                    metadata.get("langgraph_node") == MODEL_NODE_NAME
                    and isinstance(chunk, AIMessageChunk)
                    and chunk.text
                ):
                    partial.append(chunk.text)
                    response.publish(OutputTextDelta(delta=chunk.text))

            if intent is not None:
                response.publish(ResponseIntent(intent_type=intent.intent_type))
            self._remember(session, message, turn)
            response.publish(ResponseCompleted())
        except asyncio.CancelledError:
            _logger.info("Response stopped by the visitor")
            stopped = [AIMessage(content="".join(partial))] if partial else []
            self._remember(session, message, [*turn, *stopped])
            response.publish(ResponseCancelled())
            raise
        except Exception:
            _logger.exception("Chat stream failed")
            response.publish(
                ResponseFailed(
                    error=ResponseError(
                        code="CHAT_FAILED", message="Ezbot failed to respond"
                    )
                )
            )
        finally:
            response.finish()


__all__ = ["ChatService"]
