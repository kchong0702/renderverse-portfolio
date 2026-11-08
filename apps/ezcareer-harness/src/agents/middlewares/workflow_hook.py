from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any, override

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ToolCallRequest,
    hook_config,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI
from langgraph.config import get_config
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ConfigDict, Field, ValidationError


def _answer_tool(answer: type[BaseModel]) -> StructuredTool:
    """The tool the agent calls with its final answer, its arguments being the answer"""
    return StructuredTool.from_function(
        func=lambda **fields: ("Answer received", answer.model_validate(fields)),
        name=answer.__name__,
        description=f"Give your final answer as {answer.__name__}. Call it once, when you are done.",
        args_schema=answer,
        response_format="content_and_artifact",
    )


def _any_of(schema: Any) -> Any:
    """The schema with every oneOf as anyOf, which OpenAI's strict mode accepts"""
    if isinstance(schema, dict):
        return {
            "anyOf" if key == "oneOf" else key: _any_of(value)
            for key, value in schema.items()
        }
    if isinstance(schema, list):
        return [_any_of(item) for item in schema]
    return schema


class Workflow(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    response_format: type[BaseModel] | None = None
    """What the workflow wants back; the agent gets an answer tool with this as its arguments"""

    tools: tuple[BaseTool, ...] = ()
    """Tools only this workflow gives the agent"""

    hidden_tools: frozenset[str] = Field(default_factory=frozenset)
    """Names of the agent's own tools this workflow hides"""

    model: BaseChatModel | None = None
    """A model this workflow runs the agent on instead of its own"""

    strict: bool = True
    """Whether OpenAI models get the answer tool in strict mode; off for an
    answer schema strict mode refuses"""

    def config(self, config: RunnableConfig | None = None) -> RunnableConfig:
        """The run config that applies this workflow to a call of a shared agent"""
        config = config or {}
        return {
            **config,
            "configurable": {**config.get("configurable", {}), "workflow": self},
        }


def answer_of[T: BaseModel](
    messages: Sequence[AnyMessage], answer: type[T]
) -> T | None:
    """The agent's last valid answer of that type in a run's messages, if it gave one"""
    return next(
        (
            message.artifact
            for message in reversed(messages)
            if isinstance(message, ToolMessage)
            and message.name == answer.__name__
            and isinstance(message.artifact, answer)
        ),
        None,
    )


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
        """The workflow's tools and answer tool by name, described as the profile says"""
        tools = [
            *workflow.tools,
            *(
                [_answer_tool(workflow.response_format)]
                if workflow.response_format
                else []
            ),
        ]
        return {
            tool.name: tool.model_copy(
                update={"description": self.descriptions[tool.name]}
            )
            if tool.name in self.descriptions
            else tool
            for tool in tools
        }

    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call as the workflow wants it: its tools, its answer tool, its model;
        OpenAI models get the answer tool in strict mode, its schema made strict
        by OpenAI's own helper and with anyOf for oneOf"""
        workflow = _workflow()
        if workflow is None:
            return request
        model = workflow.model or request.model
        own = [
            tool
            for tool in request.tools
            if getattr(tool, "name", None) not in workflow.hidden_tools
        ]
        added = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": _any_of(
                        to_strict_json_schema(workflow.response_format)
                    ),
                    "strict": True,
                },
            }
            if workflow.response_format
            and workflow.strict
            and tool.name == workflow.response_format.__name__
            and isinstance(model, ChatOpenAI)
            else tool
            for tool in self._tools(workflow).values()
        ]
        return request.override(tools=[*own, *added], model=model)

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

    @hook_config(can_jump_to=["end"])
    @override
    def after_model(self, state: AgentState, runtime: Any) -> dict[str, Any] | None:
        """Ends the run when the model's only tool call is a valid answer, keeping
        the answer as that call's result; an invalid one goes on to fail as a tool"""
        workflow = _workflow()
        message = state["messages"][-1]
        if not (
            workflow and workflow.response_format and isinstance(message, AIMessage)
        ):
            return None
        if [call["name"] for call in message.tool_calls] != [
            workflow.response_format.__name__
        ]:
            return None
        [call] = message.tool_calls
        try:
            answer = workflow.response_format.model_validate(call["args"])
        except ValidationError:
            return None
        return {
            "messages": [
                ToolMessage(
                    "Answer received",
                    tool_call_id=call["id"],
                    name=call["name"],
                    artifact=answer,
                )
            ],
            "jump_to": "end",
        }

    @hook_config(can_jump_to=["end"])
    @override
    async def aafter_model(
        self, state: AgentState, runtime: Any
    ) -> dict[str, Any] | None:
        """Ends the run on a valid answer, as after_model does"""
        return self.after_model(state, runtime)

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
