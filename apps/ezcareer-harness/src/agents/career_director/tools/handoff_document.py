from typing import Literal

from langchain.tools import ToolRuntime
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from src.agents.career_director.state import CareerDirectorState
from src.tools import handoff


@tool
async def handoff_document(
    runtime: ToolRuntime[None, CareerDirectorState],
    agent: Literal["career-consultant"],
    document_id: str,
) -> Command | ToolMessage:
    """Hands the conversation to agent with the document document_id, as find_documents returned it this turn; agent
    answers the user about it from then on, and a document other than the graph's is new work"""
    found = runtime.state.get("document_contents", {}).get(document_id)
    if not found:
        return ToolMessage(
            f"Document {document_id} is not the best match of find_documents this turn. Find it by its title, then hand it off",
            name="handoff_document",
            tool_call_id=runtime.tool_call_id,
            status="error",
        )
    return await handoff.hand_off(
        "handoff_document",
        runtime,
        agent,
        {
            "document_id": document_id,
            "document": found.document,
            "pdf_lines": found.pdf_lines,
        },
        new_work=document_id != runtime.state.get("document_id"),
    )


handoff_document.metadata = {"handoff": True}
