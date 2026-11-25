from collections.abc import Sequence
from functools import partial, update_wrapper

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.types import Command
from pydantic import Field, create_model

from src.agents.career_director.state import CareerDirectorState
from src.tools import handoff


async def _handoff_to_child(
    document_children: frozenset[str],
    runtime: ToolRuntime[None, CareerDirectorState],
    agent: str,
    document_id: str | None = None,
) -> Command | ToolMessage:
    """Hands the conversation to agent with the named found document, which
    document_children require"""
    if agent in document_children and not document_id:
        return ToolMessage(
            f"{agent} works on a document. Find it with find_documents, then hand it off with its document_id",
            name="handoff_to_child",
            tool_call_id=runtime.tool_call_id,
            status="error",
        )
    found = runtime.state.get("document_contents", {}).get(document_id)
    if document_id and not found:
        return ToolMessage(
            f"Document {document_id} is not the best match of find_documents this turn. Find it by its title, then hand it off",
            name="handoff_to_child",
            tool_call_id=runtime.tool_call_id,
            status="error",
        )
    return await handoff.hand_off(
        "handoff_to_child",
        runtime,
        agent,
        {
            "document_id": document_id,
            "document": found.document,
            "pdf_lines": found.pdf_lines,
        }
        if found
        else {},
    )


def handoff_to_child_tool(
    children: Sequence[str], document_children: Sequence[str]
) -> BaseTool:
    """The shared handoff_to_child to one of children, extended to hand a found
    document, always to those in document_children"""
    return StructuredTool.from_function(
        coroutine=update_wrapper(
            partial(_handoff_to_child, frozenset(document_children)),
            _handoff_to_child,
        ),
        name="handoff_to_child",
        description="Hands the conversation to the child agent that owns the user's request; it answers the user from then on. Call it once per reply, with at most one document",
        args_schema=create_model(
            "HandoffToChildArgs",
            __base__=handoff.handoff_to_child_tool(children).args_schema,
            document_id=(
                str | None,
                Field(
                    default=None,
                    description="The id of the one document the child works on, as find_documents returned it this turn; only for career-consultant",
                ),
            ),
        ),
    )
