from collections.abc import Sequence

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from src.agents.career_director.state import CareerDirectorHandoffState


def build_graph(
    director: CompiledStateGraph,
    children: Sequence[CompiledStateGraph],
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    """career-director's agent graph: the director and the child agents it hands
    the conversation to, each a node named after its agent, the children told their
    parent; a turn goes to the agent the last one ended with"""
    agents = [director.name, *(child.name for child in children)]
    graph = StateGraph(CareerDirectorHandoffState)
    graph.add_conditional_edges(
        START, lambda state: state.get("active_agent", director.name), agents
    )
    graph.add_node(director.name, director)
    for child in children:
        graph.add_node(
            child.name, child.with_config(configurable={"parent_agent": director.name})
        )
    for agent in agents:
        graph.add_conditional_edges(
            agent,
            lambda state: (
                END
                if isinstance(state["messages"][-1], AIMessage)
                and not state["messages"][-1].tool_calls
                else state.get("active_agent", director.name)
            ),
            [*agents, END],
        )
    return graph.compile(checkpointer=checkpointer, name=director.name)
