from document_schema import Changeset
from langgraph.graph.state import CompiledStateGraph

from src.agents import AgentOverride
from src.features.write_document.state import EditGraphState
from src.features.write_document.tools import validate_changeset


async def run_agent(
    state: EditGraphState, agent: CompiledStateGraph, recursion_limit: int
) -> EditGraphState:
    """Runs agent on the edit with validate_changeset, keeping the changeset it
    answered with"""
    result = await agent.ainvoke(
        state,
        AgentOverride(response_format=Changeset, tools=(validate_changeset,)).config(
            {"recursion_limit": recursion_limit}
        ),
    )
    return {
        "messages": result["messages"],
        "structured_response": result.get("structured_response"),
    }
