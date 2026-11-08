from collections.abc import Awaitable, Callable, Mapping
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ToolCallRequest
from langchain_core.tools import BaseTool

from src.agents.workflow import current_workflow


class InjectToolsMiddleware(AgentMiddleware):
    def __init__(self, descriptions: Mapping[str, str]) -> None:
        """Gives the agent the calling workflow's tools; descriptions are the agent
        profile's tool descriptions, which replace a tool's own"""
        super().__init__()
        self.descriptions = descriptions

    def _tools(self) -> dict[str, BaseTool]:
        """The calling workflow's tools by name, described as the profile says"""
        workflow = current_workflow()
        return {
            tool.name: tool.model_copy(
                update={"description": self.descriptions[tool.name]}
            )
            if tool.name in self.descriptions
            else tool
            for tool in (workflow.tools if workflow else ())
        }

    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call with the workflow's tools added"""
        tools = self._tools()
        if not tools:
            return request
        return request.override(tools=[*request.tools, *tools.values()])

    def _tool_request(self, request: ToolCallRequest) -> ToolCallRequest:
        """The tool call, run with the workflow's tool when it names one"""
        tool = self._tools().get(request.tool_call["name"])
        return request.override(tool=tool) if tool else request

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> Any:
        """Runs the model call with the workflow's tools offered"""
        return handler(self._model_request(request))

    @override
    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[Any]]
    ) -> Any:
        """Runs the model call with the workflow's tools offered"""
        return await handler(self._model_request(request))

    @override
    def wrap_tool_call(
        self, request: ToolCallRequest, handler: Callable[[ToolCallRequest], Any]
    ) -> Any:
        """Runs the tool call, with the workflow's tool when it names one"""
        return handler(self._tool_request(request))

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """Runs the tool call, with the workflow's tool when it names one"""
        return await handler(self._tool_request(request))
