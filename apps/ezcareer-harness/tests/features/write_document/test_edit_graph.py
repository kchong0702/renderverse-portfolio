import json
from typing import Any

import pytest
from document_schema import AnyDocument, Changeset, FileHash, Report
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.types import Command

from src.core.config import get_settings
from src.features.write_document.flow import EditFlow
from src.features.write_document.graph import build_graph
from src.features.write_document.state import EditInput
from src.infrastructure.observability import tracing
from src.infrastructure.observability.instrumentation import instrument
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_career_consultant import (
    AGENT,
    BAD_EDIT,
    GOOD_EDIT,
    _call,
    _changeset,
    _state,
)

FLOW = EditFlow.load(get_settings().flow("edit"))

NEW_BULLET = {
    "kind": "insert_item",
    "parent": "blocks/experience/items/lumen/bullets",
    "after": "latency",
    "item": {
        "id": "k8s",
        "text": {
            "html": "Ran production workloads on Kubernetes.",
            "src": ["fact:k8s"],
        },
    },
}


async def _render(document: AnyDocument, assets: dict[FileHash, bytes]) -> Report:
    """One page holds three bullets"""
    bullets = sum(
        len(getattr(entry, "bullets", []))
        for block in document.content.blocks
        for entry in getattr(block, "items", [])
    )
    return Report(
        render_id="0" * 64, pages=1 if bullets <= 3 else 2, last_page_fill=0.5
    )


def _graph(
    *replies: AIMessage, checkpointer: Any = None
) -> tuple[Any, ScriptedChatModel]:
    model = ScriptedChatModel(replies=list(replies))
    return build_graph(AGENT, FLOW, _render, checkpointer, model), model


def _input() -> EditInput:
    state = _state()
    del state["messages"]
    return EditInput(**state, request="Mention my Kubernetes work")


def _edits(*edits: dict[str, Any]) -> list[Any]:
    return Changeset.model_validate(_changeset(*edits)).edits


async def _edit(*replies: AIMessage) -> tuple[dict[str, Any], ScriptedChatModel]:
    graph, model = _graph(*replies)
    return await graph.ainvoke(_input()), model


async def test_a_passing_changeset_goes_out_with_a_fresh_id():
    result, model = await _edit(
        _call("read_pdf_lines"),
        _call("read_profile_facts"),
        _call("read_file", file_path="/modify-career-documents/SKILL.md"),
        _call("validate_changeset", changeset=_changeset(GOOD_EDIT)),
        _call("Changeset", **_changeset(GOOD_EDIT)),
    )

    assert list(result) == ["changeset"]
    assert result["changeset"].edits == _edits(GOOD_EDIT)
    assert result["changeset"].id != "cs1"
    assert "<document>" in model.requests[0][1].text
    assert "Mention my Kubernetes work" in model.requests[0][1].text


async def test_errors_go_back_to_the_agent_until_it_fixes_them():
    result, model = await _edit(
        _call("Changeset", **_changeset(BAD_EDIT)),
        _call("Changeset", **_changeset(GOOD_EDIT)),
    )

    fix_request = [
        m
        for m in model.requests[-1]
        if isinstance(m, HumanMessage) and "checks found" in m.text
    ]
    assert fix_request and "unsupported" in fix_request[0].text
    assert result["changeset"].edits == _edits(GOOD_EDIT)


async def test_an_agent_that_never_fixes_its_changeset_fails_the_edit():
    with pytest.raises(GraphRecursionError):
        await _edit(_call("Changeset", **_changeset(BAD_EDIT)))


async def test_page_fit_removes_untouched_bullets_until_the_page_count_holds():
    result, _ = await _edit(_call("Changeset", **_changeset(NEW_BULLET)))

    [insert, delete] = result["changeset"].edits
    assert insert.kind == "insert_item"
    assert delete.kind == "delete"
    assert delete.path == "blocks/experience/items/lumen/bullets/latency"


async def test_ask_user_pauses_the_edit_until_the_user_answers():
    graph, _ = _graph(
        _call("ask_user", question="Which job?"),
        _call("Changeset", **_changeset(GOOD_EDIT)),
        checkpointer=InMemorySaver(),
    )
    run = {"configurable": {"thread_id": "t1"}}

    paused = await graph.ainvoke(_input(), run)
    done = await graph.ainvoke(Command(resume="Lumen Pay"), run)

    assert paused["__interrupt__"][0].value == "Which job?"
    assert done["changeset"].edits == _edits(GOOD_EDIT)


async def test_trace_records_each_round_of_errors_and_the_config_hash(
    make_settings, span_exporters
):
    instrument(
        make_settings(
            tracing_enabled=True,
            otlp_endpoint="http://collector:4318",
            instrumentations=["langchain"],
        )
    )

    await _edit(
        _call("Changeset", **_changeset(BAD_EDIT)),
        _call("Changeset", **_changeset(GOOD_EDIT)),
    )
    tracing.shutdown_tracing()

    [exporter] = span_exporters
    rounds = [
        json.loads(span.attributes["check.errors"])
        for span in exporter.spans
        if span.name == "checks"
    ]
    assert [[e["rule"] for e in errors] for errors in rounds] == [["unsupported"], []]
    hashes = {
        json.loads(span.attributes["metadata"]).get("agent_hash")
        for span in exporter.spans
        if "metadata" in span.attributes
    }
    assert AGENT.hash in hashes


async def test_page_fit_prints_with_the_files_from_the_input():
    printed: list[dict[FileHash, bytes]] = []

    async def render(document: AnyDocument, assets: dict[FileHash, bytes]) -> Report:
        printed.append(assets)
        return await _render(document, assets)

    model = ScriptedChatModel(replies=[_call("Changeset", **_changeset(GOOD_EDIT))])
    graph = build_graph(AGENT, FLOW, render, model=model)
    photo = "a" * 64
    state = _state()
    del state["messages"]

    await graph.ainvoke(
        EditInput.model_validate(
            {**state, "request": "Tighten it", "assets": {photo: "cGhvdG8="}}
        )
    )

    assert printed and all(assets == {photo: b"photo"} for assets in printed)


async def test_a_flow_without_checks_lets_the_changeset_through():
    model = ScriptedChatModel(replies=[_call("Changeset", **_changeset(BAD_EDIT))])
    graph = build_graph(
        AGENT, FLOW.model_copy(update={"checks": []}), _render, model=model
    )

    result = await graph.ainvoke(_input())

    assert result["changeset"].edits == _edits(BAD_EDIT)


def test_a_flow_file_naming_an_unknown_check_is_refused():
    with pytest.raises(ValueError, match="unknown checks"):
        EditFlow.model_validate({**FLOW.model_dump(), "checks": ["spelling"]})


async def test_a_document_never_printed_is_printed_once_for_its_page_count():
    printed: list[AnyDocument] = []

    async def render(document: AnyDocument, assets: dict[FileHash, bytes]) -> Report:
        printed.append(document)
        return await _render(document, assets)

    model = ScriptedChatModel(replies=[_call("Changeset", **_changeset(GOOD_EDIT))])
    graph = build_graph(AGENT, FLOW, render, model=model)
    state = _state()
    del state["messages"], state["report"]

    result = await graph.ainvoke(EditInput(**state, request="Tighten it"))

    assert result["changeset"].edits == _edits(GOOD_EDIT)
    assert printed[0] == state["document"]
    assert len(printed) == 2


async def test_an_agent_that_ends_without_a_changeset_is_asked_for_one():
    result, model = await _edit(
        AIMessage("I've checked the edit and it passes."),
        _call("Changeset", **_changeset(GOOD_EDIT)),
    )

    asked = [
        m
        for m in model.requests[-1]
        if isinstance(m, HumanMessage) and "no_changeset" in m.text
    ]
    assert asked
    assert result["changeset"].edits == _edits(GOOD_EDIT)
