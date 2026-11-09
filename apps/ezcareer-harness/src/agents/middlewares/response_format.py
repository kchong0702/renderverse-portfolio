from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)

from src.agents.agent_override import current_override


def _request(request: ModelRequest) -> ModelRequest:
    """The model call with the override's response_format, or none"""
    agent_override = current_override()
    return request.override(
        response_format=agent_override and agent_override.response_format
    )


class ResponseFormatMiddleware(AgentMiddleware):
    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call with the override's response_format"""
        return handler(_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call with the override's response_format"""
        return await handler(_request(request))
