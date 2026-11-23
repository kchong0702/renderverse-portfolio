from collections.abc import Sequence
from functools import partial, update_wrapper
from typing import Literal

from langchain.agents import AgentState
from langchain.tools import ToolRuntime
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool, tool
from langgraph.config import get_config
from langgraph.types import Command
from pydantic import ConfigDict, Field, create_model

ONE_AT_A_TIME = "Hand off one at a time; this handoff did not run"
"""What a handoff call after the first in the same reply returns"""


def parent_agent() -> str | None:
    """The agent the current run hands back to, set only when the run is a child
    node of an agent graph"""
    return get_config().get("configurable", {}).get("parent_agent")


async def _handoff(
    name: str,
    runtime: ToolRuntime[None, AgentState],
    agent: str,
    document_id: str | None = None,
) -> Command | ToolMessage:
    """Moves the conversation to agent's node in the parent graph with the named found
    document, answering each of the reply's tool calls; only the first handoff runs"""
    call = next(
        m for m in reversed(runtime.state["messages"]) if isinstance(m, AIMessage)
    )
    handoffs = ("handoff_to_child", "handoff_to_parent")
    if runtime.tool_call_id != next(
        c["id"] for c in call.tool_calls if c["name"] in handoffs
    ):
        return ToolMessage(
            ONE_AT_A_TIME, name=name, tool_call_id=runtime.tool_call_id, status="error"
        )
    found = runtime.state.get("found_documents", {}).get(document_id)
    if document_id and not found:
        return ToolMessage(
            f"Document {document_id} is not the best match of find_documents this turn. Find it by its title, then hand it off",
            name=name,
            tool_call_id=runtime.tool_call_id,
            status="error",
        )
    return Command(
        goto=agent,
        update={
            "active_agent": agent,
            "document_id": document_id if found else None,
            "document": found.document if found else None,
            "lines": found.lines if found else None,
            "messages": [
                call,
                *(
                    ToolMessage(
                        f"Handed the conversation to {agent}",
                        name=name,
                        tool_call_id=c["id"],
                        artifact={"step_detail": agent},
                    )
                    if c["id"] == runtime.tool_call_id
                    else ToolMessage(
                        ONE_AT_A_TIME
                        if c["name"] in handoffs
                        else f"Its result was dropped, as the conversation was handed to {agent}",
                        name=c["name"],
                        tool_call_id=c["id"],
                        status="error",
                    )
                    for c in call.tool_calls
                ),
            ],
        },
        graph=Command.PARENT,
    )


def handoff_to_child_tool(children: Sequence[str]) -> BaseTool:
    """handoff_to_child, which hands the conversation to one of the child agents
    named in children"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(partial(_handoff, "handoff_to_child"), _handoff),
        name="handoff_to_child",
        description="Hands the conversation to the child agent that owns the user's request; it answers the user from then on. Call it once per reply, with at most one document",
        args_schema=create_model(
            "HandoffToChildArgs",
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            runtime=(
                ToolRuntime[None, AgentState],
                Field(
                    description="The agent's state, injected by the agent and never set by the model"
                ),
            ),
            agent=(Literal[*children], Field(description="The child agent's name")),
            document_id=(
                str | None,
                Field(
                    default=None,
                    description="The id of the one document the child works on, as find_documents returned it this turn; only for career-consultant",
                ),
            ),
        ),
    )


@tool
async def handoff_to_parent(
    runtime: ToolRuntime[None, AgentState],
) -> Command | ToolMessage:
    """Hands the conversation back to the agent that handed it to you, when the
    user's message is not yours to answer"""
    return await _handoff(
        "handoff_to_parent", runtime, runtime.config["configurable"]["parent_agent"]
    )
