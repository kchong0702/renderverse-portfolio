from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage

from src.agents.prompt import read_prompt
from src.core.config import get_settings
from src.tools.handoff import handoff_to_parent, parent_agent


def _request(request: ModelRequest, hand_back: str) -> ModelRequest:
    """The model call told to hand back what is outside its scope when the run is a
    child node of an agent graph, and offered handoff_to_parent only then"""
    if parent_agent():
        return request.override(
            system_message=SystemMessage(
                content=[
                    *(
                        request.system_message.content_blocks
                        if request.system_message
                        else []
                    ),
                    {"type": "text", "text": hand_back},
                ]
            )
        )
    return request.override(
        tools=[
            tool
            for tool in request.tools
            if (tool["name"] if isinstance(tool, dict) else tool.name)
            != handoff_to_parent.name
        ]
    )


class ParentHandoffMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        """Registers handoff_to_parent, the tool a child agent hands back with, and
        reads the hand-back instruction from its prompt file"""
        super().__init__()
        self.tools = [handoff_to_parent]
        self.hand_back = read_prompt(
            get_settings().middleware_prompts / "parent_handoff.md"
        )
        """What a child agent is told to do with a message that isn't its to answer"""

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call with the instruction and tools for its place in a graph"""
        return handler(_request(request, self.hand_back))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call with the instruction and tools for its place in a graph"""
        return await handler(_request(request, self.hand_back))
