from functools import partial
from typing import Literal

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer

from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import get_settings
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.nodes import extract, render, structure, verify
from src.features.import_document.schemas import ImportInput, ImportResult
from src.features.import_document.state import ImportState


def _after_verify(state: ImportState) -> Literal["structure", "render"]:
    """Prints a reply that passed the checks; sends one that failed back to
    structure while steps remain for structure, verify and render"""
    if not state["errors"]:
        return "render"
    if state["remaining_steps"] < 3:
        raise ImportFailed(
            "the résumé didn't pass its checks: "
            + "; ".join(f"{e.at} ({e.rule}): {e.message}" for e in state["errors"])
        )
    return "structure"


def build_graph(
    agent: CompiledStateGraph,
    artifact_service: ArtifactServiceClient,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    """The import-resume graph run on agent, with the configurations the settings
    name, converting and printing through artifact_service; checkpointer keeps runs"""
    configurations = (
        get_settings().graph_profile("import-resume").load(ImportResumeConfigurations)
    )
    graph = StateGraph(
        ImportState, input_schema=ImportInput, output_schema=ImportResult
    )
    graph.add_node("extract", partial(extract, artifact_service=artifact_service))
    graph.add_node("structure", partial(structure, agent=agent))
    graph.add_node("verify", partial(verify, configurations=configurations))
    graph.add_node("render", partial(render, artifact_service=artifact_service))
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "structure")
    graph.add_edge("structure", "verify")
    graph.add_conditional_edges("verify", _after_verify)
    graph.add_edge("render", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit,
        metadata={"flow": "import-resume"},
    )
