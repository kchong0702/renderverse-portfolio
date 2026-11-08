from collections.abc import Awaitable, Callable
from typing import Any, override

from langchain.agents.middleware import AgentMiddleware, ModelRequest

from src.agents.workflow import current_workflow


def _request(request: ModelRequest) -> ModelRequest:
    """The model call with the calling workflow's response_format, or none; LangChain
    picks native output or an answer tool for the model"""
    workflow = current_workflow()
    return request.override(response_format=workflow and workflow.response_format)


class ResponseFormatMiddleware(AgentMiddleware):
    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Any]
    ) -> Any:
        """Runs the model call for the workflow's answer"""
        return handler(_request(request))

    @override
    async def awrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], Awaitable[Any]]
    ) -> Any:
        """Runs the model call for the workflow's answer"""
        return await handler(_request(request))
