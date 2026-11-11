from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)

from src.agents.agent_override import current_override


class AllowedToolsMiddleware(AgentMiddleware):
    def __init__(self, own: set[str]) -> None:
        """Offers only the agent's own tools the run's override allows"""
        super().__init__()
        self.own = own
        """Names of the tools the agent was built with"""

    def _request(self, request: ModelRequest) -> ModelRequest:
        """The model call without the agent's tools the override leaves out"""
        agent_override = current_override()
        if agent_override is None or agent_override.tools is None:
            return request
        if unknown := agent_override.tools - self.own:
            raise ValueError(
                f"The override allows tools the agent lacks: {sorted(unknown)}"
            )
        return request.override(
            tools=[
                tool
                for tool in request.tools
                if (tool["name"] if isinstance(tool, dict) else tool.name)
                not in self.own - agent_override.tools
            ]
        )

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call offering only the tools the override allows"""
        return handler(self._request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call offering only the tools the override allows"""
        return await handler(self._request(request))
