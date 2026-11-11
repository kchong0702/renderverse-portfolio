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
    """career-director and the child agents it hands the conversation to, each a
    node named after its agent; a turn goes to the agent the last one ended with"""
    agents = [director.name, *(child.name for child in children)]
    graph = StateGraph(CareerDirectorHandoffState)
    graph.add_conditional_edges(
        START, lambda state: state.get("active_agent", director.name), agents
    )
    for agent in (director, *children):
        graph.add_node(agent.name, agent)
        graph.add_conditional_edges(
            agent.name,
            lambda state: (
                END
                if isinstance(state["messages"][-1], AIMessage)
                and not state["messages"][-1].tool_calls
                else state.get("active_agent", director.name)
            ),
            [*agents, END],
        )
    return graph.compile(checkpointer=checkpointer, name=director.name)
