from collections.abc import Sequence
from functools import partial, update_wrapper
from typing import Literal

from langchain.agents import AgentState
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import ConfigDict, Field, create_model


async def _handoff(
    tool: str, runtime: ToolRuntime[None, AgentState], agent: str
) -> Command:
    """Moves the conversation to agent's node in the parent graph, passing on the
    call that asked for it with its answer"""
    call = next(
        m for m in reversed(runtime.state["messages"]) if isinstance(m, AIMessage)
    )
    return Command(
        goto=agent,
        update={
            "active_agent": agent,
            "messages": [
                call,
                ToolMessage(
                    f"Handed the conversation to {agent}",
                    name=tool,
                    tool_call_id=runtime.tool_call_id,
                    artifact={"step_detail": agent},
                ),
            ],
        },
        graph=Command.PARENT,
    )


_RUNTIME = (
    ToolRuntime[None, AgentState],
    Field(
        description="The agent's state, injected by the agent and never set by the model"
    ),
)


def handoff_to_child_tool(children: Sequence[str]) -> BaseTool:
    """handoff_to_child, which hands the conversation to one of the child agents
    named in children"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_handoff, "handoff_to_child"), _handoff),
        name="handoff_to_child",
        description="Hands the conversation to the child agent that owns the user's request; it answers the user from then on",
        args_schema=create_model(
            "HandoffToChildArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=_RUNTIME,
            agent=(Literal[*children], Field(description="The child agent's name")),
        ),
    )


def handoff_to_parent_tool(parent: str) -> BaseTool:
    """handoff_to_parent, which hands the conversation back to parent"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_handoff, "handoff_to_parent", agent=parent), _handoff
        ),
        name="handoff_to_parent",
        description="Hands the conversation back to the agent that handed it to you, when the user's message is not yours to answer",
        args_schema=create_model(
            "HandoffToParentArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=_RUNTIME,
        ),
    )
