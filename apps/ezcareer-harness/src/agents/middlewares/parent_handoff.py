from collections.abc import Awaitable, Callable
from typing import override

from langchain.agents.middleware import (
    AgentMiddleware,
    ModelCallResult,
    ModelRequest,
    ModelResponse,
)
from langchain_core.messages import SystemMessage

from src.tools.handoff import handoff_to_parent, parent_agent

HAND_BACK = (
    "When a message is outside your scope, call `handoff_to_parent` and write "
    "nothing else. The agent that handed you the conversation answers it."
)
"""What a child agent is told to do with a message that isn't its to answer"""

DECLINE = "When a message is outside your scope, say plainly that you can't help with that here."
"""What an agent served on its own is told to do with a message that isn't its to answer"""


def _request(request: ModelRequest) -> ModelRequest:
    """The model call told what to do outside its scope, and offered handoff_to_parent
    only when the run is a child node of an agent graph"""
    child = bool(parent_agent())
    return request.override(
        system_message=SystemMessage(
            content=[
                *(
                    request.system_message.content_blocks
                    if request.system_message
                    else []
                ),
                {"type": "text", "text": HAND_BACK if child else DECLINE},
            ]
        ),
        tools=[
            tool
            for tool in request.tools
            if child
            or (tool["name"] if isinstance(tool, dict) else tool.name)
            != handoff_to_parent.name
        ],
    )


class ParentHandoffMiddleware(AgentMiddleware):
    def __init__(self) -> None:
        """Registers handoff_to_parent, the tool a child agent hands back with"""
        super().__init__()
        self.tools = [handoff_to_parent]

    @override
    def wrap_model_call(
        self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]
    ) -> ModelCallResult:
        """Runs the model call with the instruction and tools for its place in a graph"""
        return handler(_request(request))

    @override
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        """Runs the model call with the instruction and tools for its place in a graph"""
        return await handler(_request(request))
