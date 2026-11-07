import httpx
from langchain_core.language_models import BaseChatModel
from langgraph.pregel import Pregel
from langgraph.types import Checkpointer

from src.agents import load_agents
from src.core.config import get_settings
from src.features.write_document.agent import TEMPLATES
from src.features.write_document.graph import build_graph
from src.features.write_document.profile import EditProfile
from src.features.write_document.render import render_with
from src.features.write_document.state import Render
from src.shared.clients.artifact_service import ArtifactService


def artifact_service_render() -> Render:
    """Prints through the artifact-service the settings name"""
    client = httpx.AsyncClient(
        base_url=get_settings().app.artifact_service_url, timeout=60
    )
    return render_with(ArtifactService(client), TEMPLATES)


def edit_graph(
    render: Render,
    checkpointer: Checkpointer = None,
    model: BaseChatModel | None = None,
) -> Pregel:
    """The edit graph, built from the registered career-consultant and the edit
    graph's profile; model replaces the agent's own"""
    settings = get_settings()
    return build_graph(
        load_agents(settings.agents)["career-consultant"],
        settings.graph_profile("edit").load(EditProfile),
        render,
        checkpointer,
        model,
    )
