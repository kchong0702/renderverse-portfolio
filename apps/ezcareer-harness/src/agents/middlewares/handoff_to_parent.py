from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)

from src.tools.handoff import handoff_to_parent, parent_agent


def _request(request: ModelRequest) -> ModelRequest:
    """The model call without handoff_to_parent unless the run is a child node of
    an agent graph"""
    if parent_agent():
        return request
    return request.override(
        tools=[
            tool
            for tool in request.tools
            if (tool["name"] if isinstance(tool, dict) else tool.name)
            != handoff_to_parent.name
        ]
    )


class HandoffToParentMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        """Registers handoff_to_parent, the tool a child agent hands back with"""
        super().__init__()
        self.tools = [handoff_to_parent]

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call offering handoff_to_parent only inside an agent graph"""
        return handler(_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call offering handoff_to_parent only inside an agent graph"""
        return await handler(_request(request))
