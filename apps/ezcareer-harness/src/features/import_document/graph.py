from functools import partial

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.clients.artifact_service import ArtifactServiceClient
from src.clients.llm_providers import llm_provider
from src.core.config import get_settings
from src.features.import_document.configurations import ImportResumeConfigurations
from src.features.import_document.nodes import extract, structure
from src.features.import_document.schemas import ImportInput
from src.features.import_document.state import ImportState


def build_graph(
    artifact_service: ArtifactServiceClient, model: BaseChatModel | None = None
) -> CompiledStateGraph:
    """The import-resume graph on its graph profile, converting the upload through
    artifact_service; model replaces the configured LLM"""
    settings = get_settings()
    profile = settings.graph_profile("import-resume")
    configurations = profile.load(ImportResumeConfigurations)
    graph = StateGraph(ImportState, input_schema=ImportInput)
    graph.add_node("extract", partial(extract, artifact_service=artifact_service))
    graph.add_node(
        "structure",
        partial(
            structure,
            model=model or llm_provider(configurations.family, configurations.model),
            prompt=(profile.folder / "system.md").read_text(),
        ),
    )
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "structure")
    graph.add_edge("structure", END)
    return graph.compile()
