from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.pregel import Pregel
from langgraph.types import Checkpointer

from src.features.write_document.nodes import brief, page_fit, validate
from src.features.write_document.state import EditContext, EditGraphState

RECURSION_LIMIT = 12
"""Graph steps before an edit fails; each check round takes two"""


def build_graph(agent: Pregel, checkpointer: Checkpointer = None) -> Pregel:
    """Turns a chat request into a checked changeset that fits the page"""

    async def run_agent(state: EditGraphState, config: RunnableConfig) -> dict:
        """Runs the agent under its own recursion limit instead of the graph's"""
        own = {key: value for key, value in config.items() if key != "recursion_limit"}
        return await agent.ainvoke(state, own)

    graph = StateGraph(EditGraphState, context_schema=EditContext)
    graph.add_node("brief", brief)
    graph.add_node("agent", run_agent)
    graph.add_node("validate", validate)
    graph.add_node("page_fit", page_fit)
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
        recursion_limit=RECURSION_LIMIT
    )
