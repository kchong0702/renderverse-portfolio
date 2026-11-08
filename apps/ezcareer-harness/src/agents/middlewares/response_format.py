from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)

from src.agents.workflow import current_workflow


def _request(request: ModelRequest) -> ModelRequest:
    """The model call with the calling workflow's response_format, or none; LangChain
    picks native output or an answer tool for the model"""
    workflow = current_workflow()
    return request.override(response_format=workflow and workflow.response_format)


class ResponseFormatMiddleware(AgentMiddleware):
    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call with the workflow's response_format"""
        return handler(_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call with the workflow's response_format"""
        return await handler(_request(request))
