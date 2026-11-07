from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel
from langgraph.types import Checkpointer

from src.agents import Agent
from src.features.write_document.agent import career_consultant
from src.features.write_document.nodes import brief, page_fit, validate
from src.features.write_document.profile import EditProfile
from src.features.write_document.state import (
    EditGraphState,
    EditInput,
    EditOutput,
    Render,
)


def build_graph(
    agent: Agent,
    profile: EditProfile,
    render: Render,
    checkpointer: Checkpointer = None,
    model: BaseChatModel | None = None,
) -> Pregel:
    """Turns a chat request into a checked changeset that fits the page, with the
    registered career-consultant and the graph's profile; model replaces
    the agent's own"""
    consultant = career_consultant(agent, model)

    async def run_agent(state: EditGraphState, config: RunnableConfig) -> dict:
        """Runs career-consultant under its own recursion limit"""
        return await consultant.ainvoke(
            state, {**config, "recursion_limit": profile.agent_recursion_limit}
        )

    async def fit(state: EditGraphState) -> dict:
        """Fits the changeset to the page with the graph's render function"""
        return await page_fit(state, render, profile.page_fit_trims)

    graph = StateGraph(EditGraphState, input_schema=EditInput, output_schema=EditOutput)
    graph.add_node("brief", brief)
    graph.add_node("agent", run_agent)
    graph.add_node("validate", lambda state: validate(state, profile.checks))
    graph.add_node("page_fit", fit)
    graph.add_edge(START, "brief")
    graph.add_edge("brief", "agent")
    graph.add_edge("agent", "validate")
    graph.add_conditional_edges(
        "validate",
        lambda state: "agent" if state["errors"] else "page_fit",
        ["agent", "page_fit"],
    )
    graph.add_edge("page_fit", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=profile.recursion_limit
    )
