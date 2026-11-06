from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.features.import_document.nodes import extract, structure
from src.features.import_document.state import ImportContext, ImportState


def build_graph() -> CompiledStateGraph:
    """Turns an uploaded résumé into content that cites its lines"""
    graph = StateGraph(ImportState, context_schema=ImportContext)
    graph.add_node("extract", extract)
    graph.add_node("structure", structure)
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "structure")
    graph.add_edge("structure", END)
    return graph.compile()
