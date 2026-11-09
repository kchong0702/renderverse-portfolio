from collections.abc import Awaitable, Callable, Mapping
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

from src.agents.agent_override import current_override


class InjectToolsMiddleware(AgentMiddleware):
    def __init__(self, descriptions: Mapping[str, str]) -> None:
        """Gives the agent the override's tools and describes every tool it is
        offered with descriptions, the agent profile's, over a tool's own"""
        super().__init__()
        self.descriptions = descriptions
        """The agent profile's tool descriptions, by tool name"""

    def _described[T: BaseTool | dict](self, tool: T) -> T:
        """tool with the profile's description, when the profile has one for it"""
        if isinstance(tool, BaseTool) and tool.name in self.descriptions:
            return tool.model_copy(update={"description": self.descriptions[tool.name]})
        return tool

    def _tools(self) -> dict[str, BaseTool]:
        """The override's tools by name, described as the profile says"""
        agent_override = current_override()
        return {
            tool.name: self._described(tool)
            for tool in (agent_override.tools if agent_override else ())
        }

    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call with the override's tools added and every tool described
        as the profile says"""
        return request.override(
            tools=[
                *(self._described(tool) for tool in request.tools),
                *self._tools().values(),
            ]
        )

    def _tool_request(self, request: ToolCallRequest) -> ToolCallRequest:
        """The tool call, run with the override's tool when it names one"""
        tool = self._tools().get(request.tool_call["name"])
        return request.override(tool=tool) if tool else request

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call with the override's tools offered, described as the profile says"""
        return handler(self._model_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call with the override's tools offered, described as the profile says"""
        return await handler(self._model_request(request))

    @override
    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        """Runs the tool call, with the override's tool when it names one"""
        return handler(self._tool_request(request))

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command]],
    ) -> ToolMessage | Command:
        """Runs the tool call, with the override's tool when it names one"""
        return await handler(self._tool_request(request))
