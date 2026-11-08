from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ToolCallRequest,
    hook_config,
)
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import StructuredTool
from langchain_openai import ChatOpenAI
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ValidationError

from src.agents.workflow import current_workflow


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


def _answer_format() -> type[BaseModel] | None:
    """The calling workflow's response_format, if it wants one"""
    workflow = current_workflow()
    return workflow.response_format if workflow else None


class AnswerToolMiddleware(AgentMiddleware):
    def _model_request(self, request: ModelRequest) -> ModelRequest:
        """The model call with the workflow's answer tool added, unless the agent has
        a native response_format; OpenAI gets it strict, with anyOf for oneOf"""
        workflow = current_workflow()
        answer = workflow and workflow.response_format
        if answer is None or request.response_format is not None:
            return request
        tool = _answer_tool(answer)
        if workflow.strict and isinstance(request.model, ChatOpenAI):
            tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": _any_of(to_strict_json_schema(answer)),
                    "strict": True,
                },
            }
        return request.override(tools=[*request.tools, tool])

    def _tool_request(self, request: ToolCallRequest) -> ToolCallRequest:
        """The tool call, run with the answer tool when it names it"""
        answer = _answer_format()
        if answer is None or request.tool_call["name"] != answer.__name__:
            return request
        return request.override(tool=_answer_tool(answer))

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> Any:
        """Runs the model call with the answer tool offered"""
        return handler(self._model_request(request))

    @override
    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[Any]]
    ) -> Any:
        """Runs the model call with the answer tool offered"""
        return await handler(self._model_request(request))

    @hook_config(can_jump_to=["end"])
    @override
    def after_model(self, state: AgentState, runtime: Any) -> dict[str, Any] | None:
        """Ends the run when the model's only tool call is a valid answer, putting it
        in structured_response; an invalid one goes on to fail as a tool"""
        answer = _answer_format()
        message = state["messages"][-1]
        if not (answer and isinstance(message, AIMessage)):
            return None
        if [call["name"] for call in message.tool_calls] != [answer.__name__]:
            return None
        [call] = message.tool_calls
        try:
            response = answer.model_validate(call["args"])
        except ValidationError:
            return None
        return {
            "messages": [
                ToolMessage(
                    "Answer received",
                    tool_call_id=call["id"],
                    name=call["name"],
                    artifact=response,
                )
            ],
            "structured_response": response,
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
        """Runs the tool call, with the answer tool when it names it"""
        return handler(self._tool_request(request))

    @override
    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[Any]],
    ) -> Any:
        """Runs the tool call, with the answer tool when it names it"""
        return await handler(self._tool_request(request))
