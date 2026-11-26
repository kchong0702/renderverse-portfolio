from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware
from langchain.agents.middleware.types import ToolCallRequest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.types import Command


class DuplicateTaskGuardMiddleware(AgentMiddleware):
    def _duplicate(self, request: ToolCallRequest) -> ToolMessage | None:
        """An error answer to a document task whose document an earlier call in the
        same reply already has a task on; None for any other call"""
        call = request.tool_call
        if call["name"] != "assign_career_consultant_task":
            return None
        reply = next(
            m for m in reversed(request.state["messages"]) if isinstance(m, AIMessage)
        )
        first = next(
            c["id"]
            for c in reply.tool_calls
            if c["name"] == call["name"]
            and c["args"].get("document_id") == call["args"].get("document_id")
        )
        if first == call["id"]:
            return None
        return ToolMessage(
            f"Document {call['args'].get('document_id')} already has a task in this reply, so this one did not run. Put everything for one document in one task",
            name=call["name"],
            tool_call_id=call["id"],
            status="error",
        )

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        """Runs the tool call unless it repeats a document task in the same reply"""
        return self._duplicate(request) or handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        """Runs the tool call unless it repeats a document task in the same reply"""
        return self._duplicate(request) or await handler(request)
