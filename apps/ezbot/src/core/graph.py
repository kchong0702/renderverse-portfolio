from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.graph.state import CompiledStateGraph

RESPOND_NODE_NAME = "respond"


def build_chat_graph(model: BaseChatModel) -> CompiledStateGraph:
    """Build the chat graph, a single node replying to the conversation so far"""

    async def respond(state: MessagesState) -> dict:
        return {"messages": [await model.ainvoke(state["messages"])]}

    builder = StateGraph(MessagesState)
    builder.add_node(RESPOND_NODE_NAME, respond)
    builder.add_edge(START, RESPOND_NODE_NAME)
    builder.add_edge(RESPOND_NODE_NAME, END)
    return builder.compile(name="ezbot")


__all__ = ["RESPOND_NODE_NAME", "build_chat_graph"]
