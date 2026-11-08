from collections.abc import Awaitable, Callable, Mapping
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ToolCallRequest
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool
from langgraph.config import get_config
from pydantic import BaseModel, ConfigDict, Field


class Workflow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    answer: type[BaseModel]
    """What the agent answers with on this call; one of the answers it was built with"""

    tools: tuple[BaseTool, ...] = ()
    """Tools only this workflow gives the agent"""

    hidden_tools: frozenset[str] = Field(default_factory=frozenset)
    """Names of the agent's own tools this workflow hides"""

    model: BaseChatModel | None = None
    """A model this workflow runs the agent on instead of its own"""

    def config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """The run config that applies this workflow to a call of a shared agent"""
        config = config or {}
        return {
            **config,
            "configurable": {**config.get("configurable", {}), "workflow": self},
        }


def _workflow() -> Workflow | None:
    """The workflow the current run's config names, if any"""
    return get_config().get("configurable", {}).get("workflow")


class WorkflowHook(AgentMiddleware):
    def __init__(self, descriptions: Mapping[str, str]) -> None:
        """Applies the calling workflow to every model and tool call; descriptions
        are the agent profile's tool descriptions, given to the workflow's tools too"""
        super().__init__()
        self.descriptions = descriptions

    def _tools(self, workflow: Workflow) -> dict[str, BaseTool]:
        """The workflow's own tools by name, described as the agent's profile says"""
        return {
            tool.name: tool.model_copy(
                update={"description": self.descriptions[tool.name]}
            )
            if tool.name in self.descriptions
            else tool
            for tool in workflow.tools
        }

    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call as the workflow wants it: its answer, its tools, its model"""
        workflow = _workflow()
        if workflow is None:
            return request
        own = [
            tool
            for tool in request.tools
            if getattr(tool, "name", None) not in workflow.hidden_tools
        ]
        return request.override(
            tools=[*own, *self._tools(workflow).values()],
            response_format=workflow.answer,
            model=workflow.model or request.model,
        )

    def _tool_request(self, request: ToolCallRequest) -> ToolCallRequest:
        """The tool call, run with the workflow's tool when it names one"""
        workflow = _workflow()
        tool = workflow and self._tools(workflow).get(request.tool_call["name"])
        return request.override(tool=tool) if tool else request

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> Any:
        """Runs the model call with the workflow applied"""
        return handler(self._model_request(request))

    @override
    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[Any]]
    ) -> Any:
        """Runs the model call with the workflow applied"""
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
