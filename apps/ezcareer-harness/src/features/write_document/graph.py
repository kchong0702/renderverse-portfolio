from functools import partial

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import get_settings
from src.features.write_document.configurations import WriteDocumentConfigurations
from src.features.write_document.nodes import brief, load, output, page_fit
from src.features.write_document.state import EditGraphState
from src.features.write_document.types import EditInput, EditOutput


def build_graph(
    agent: CompiledStateGraph,
    artifact_service: ArtifactServiceClient,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    """The write-document graph run on agent, with the configurations the settings
    name, printing through artifact_service; checkpointer keeps its runs"""
    configurations = (
        get_settings().graph_profile("write-document").load(WriteDocumentConfigurations)
    )
    graph = StateGraph(EditGraphState, input_schema=EditInput, output_schema=EditOutput)
    graph.add_node("load", load)
    graph.add_node("brief", brief)
    graph.add_node("agent", agent)
    graph.add_node(
        "page_fit",
        partial(
            page_fit,
            artifact_service=artifact_service,
            trims=configurations.page_fit_trims,
        ),
    )
    graph.add_node("output", output)
    graph.add_edge(START, "load")
    graph.add_edge("load", "brief")
    graph.add_edge("brief", "agent")
    graph.add_conditional_edges(
        "agent", lambda state: "page_fit" if state.get("changeset") else "output"
    )
    graph.add_edge("page_fit", "output")
    graph.add_edge("output", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit,
        metadata={"flow": "write-document"},
    )
