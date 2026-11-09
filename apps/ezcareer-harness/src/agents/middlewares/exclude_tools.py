from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
    ToolCallRequest,
)
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool
from langgraph.types import Command


class ExcludeToolsMiddleware(AgentMiddleware):
    def __init__(self, excluded: frozenset[str]) -> None:
        """Keeps the agent from seeing or calling the excluded tools"""
        super().__init__()
        self.excluded = excluded
        """Names of the tools the agent is never offered"""

    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call without the excluded tools"""
        return request.override(
            tools=[
                tool
                for tool in request.tools
                if (tool.name if isinstance(tool, BaseTool) else tool.get("name"))
                not in self.excluded
            ]
        )

    def _refusal(self, request: ToolCallRequest) -> ToolMessage | None:
        """The error a call to an excluded tool gets instead of running"""
        name = request.tool_call["name"]
        if name not in self.excluded:
            return None
        return ToolMessage(
            f"Error: {name} is not available.",
            tool_call_id=request.tool_call["id"] or "",
            name=name,
            status="error",
        )

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call without the excluded tools"""
        return handler(self._model_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call without the excluded tools"""
        return await handler(self._model_request(request))

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Refuses a call to an excluded tool and runs any other"""
        return self._refusal(request) or handler(request)

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Refuses a call to an excluded tool and runs any other"""
        return self._refusal(request) or await handler(request)
