from typing import Literal

import pytest
from document_schema import AnyDocument, DocumentKind
from langgraph.checkpoint.serde.event_hooks import register_serde_event_listener
from pydantic import TypeAdapter

from src.agents.career_director.types import DocumentContent
from src.app.container import Container
from src.core.config import get_settings
from src.shared.profile import Preferences
from tests.agents.career_consultant import test_career_consultant as career_consultant


def test_the_container_reads_the_agent_registry_once():
    container = Container()

    assert container.registry() is container.registry()
    assert set(container.registry()) == {a.name for a in container.settings().agents}


def test_workflow_graphs_keep_runs_in_the_containers_checkpointer():
    container = Container()

    graphs = [e.graph for e in container.executables() if e.kind == "workflow"]

    assert [graph.checkpointer for graph in graphs] == [container.checkpointer()] * 7


@pytest.mark.parametrize("stores", ["memory", "postgres"])
async def test_thread_state_reads_back_as_the_harness_types_with_none_unregistered(
    stores: Literal["memory", "postgres"],
):
    container = Container()
    container.settings.override(get_settings().model_copy(update={"stores": stores}))
    container.executables()
    state = career_consultant._state()
    letter = TypeAdapter(AnyDocument).validate_python(career_consultant.LETTER)
    values = {
        **state,
        "preferences": Preferences(work_modes=["remote"]),
        "document_contents": {"doc-2": DocumentContent(document=letter, pdf_lines=[])},
        "changeset": career_consultant._changeset(career_consultant.GOOD_EDIT),
        "kind": DocumentKind.COVER_LETTER,
    }
    events: list[object] = []
    unregister = register_serde_event_listener(events.append)

    serde = container.checkpointer().serde
    read = serde.loads_typed(serde.dumps_typed(values))
    unregister()

    assert read == values
    assert events == []
