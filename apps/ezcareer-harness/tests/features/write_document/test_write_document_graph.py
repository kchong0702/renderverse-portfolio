import json
from functools import partial

import httpx
import pytest
from document_schema import (
    AnyDocument,
    AnyEdit,
    Experience,
    InsertBlock,
    InsertItem,
    RichValue,
)
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer, Command
from pydantic import TypeAdapter

from src.clients.artifact_service import ArtifactServiceClient
from src.core.errors import ExecuteError
from src.features.write_document.graph import build_graph
from src.features.write_document.types import EditInput, EditOutput
from src.infrastructure.observability import tracing
from src.infrastructure.observability.instrumentation import instrument
from tests.agents.career_consultant.test_career_consultant import (
    AGENT,
    GOOD_EDIT,
    _agent,
    _answer,
    _model,
    _state,
)
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.write_document.test_validate_changeset import BAD_EDIT

NEW_BULLET = InsertItem(
    kind="insert_item",
    parent="blocks/experience/items/lumen/bullets",
    after="latency",
    item={
        "id": "k8s",
        "text": RichValue(
            html="Ran production workloads on Kubernetes.", src=["fact:k8s"]
        ).model_dump(mode="json"),
    },
)

PLATFORM_JOB = {
    "id": "platform",
    "role": {"text": "Senior Engineer", "src": ["p1.s6"]},
    "company": {"text": "Lumen Pay", "src": ["fact:k8s"]},
    "bullets": [
        {
            "id": "k8s",
            "text": {
                "html": "Ran production workloads on Kubernetes.",
                "src": ["fact:k8s"],
            },
        },
        {
            "id": "mentoring",
            "text": {
                "html": "Mentored 4 junior engineers.",
                "src": ["fact:mentoring"],
            },
        },
    ],
}


def _print(request: httpx.Request, sent: list[httpx.Request]) -> httpx.Response:
    """Records the request and prints one page for up to three bullets, two for more"""
    sent.append(request)
    document = TypeAdapter(AnyDocument).validate_python(
        json.loads(request.content)["document"]
    )
    bullets = sum(
        len(job.bullets)
        for block in document.content.blocks
        if isinstance(block, Experience)
        for job in block.items
    )
    return httpx.Response(
        200,
        json={
            "artifact": "JVBERg==",
            "report": {
                "render_id": "0" * 64,
                "pages": 1 if bullets <= 3 else 2,
                "last_page_fill": 0.5,
            },
        },
    )


def _fail(request: httpx.Request) -> httpx.Response:
    """Fails every print"""
    return httpx.Response(500)


def _graph(
    model: ScriptedChatModel,
    sent: list[httpx.Request] | None = None,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    return build_graph(
        _agent(model),
        ArtifactServiceClient(
            httpx.AsyncClient(
                transport=httpx.MockTransport(
                    partial(_print, sent=[] if sent is None else sent)
                ),
                base_url="http://artifact-service",
            ),
        ),
        checkpointer,
    )


def _input(**update: object) -> EditInput:
    state = _state()
    return EditInput(
        request="Mention my Kubernetes work",
        document=state["document"],
        lines=state["lines"],
        facts=state["facts"],
    ).model_copy(update=update)


async def _edit(*replies: AIMessage) -> tuple[EditOutput, ScriptedChatModel]:
    model = _model(*replies)
    return await _graph(model).ainvoke(_input()), model


async def test_a_passing_changeset_goes_out_with_a_fresh_id():
    result, model = await _edit(
        _call("read_pdf_lines"),
        _call("read_profile_facts"),
        _call("read_file", file_path="/modify-career-documents/SKILL.md"),
        _answer(GOOD_EDIT),
    )

    assert list(result) == ["changeset"]
    assert result["changeset"].edits == [GOOD_EDIT]
    assert result["changeset"].id != "cs1"
    assert "<document>" in model.requests[0][1].text
    assert "Mention my Kubernetes work" in model.requests[0][1].text


async def test_errors_go_back_to_the_agent_until_it_fixes_them():
    result, model = await _edit(_answer(BAD_EDIT), _answer(GOOD_EDIT))

    [fix_request] = [
        m
        for m in model.requests[-1]
        if isinstance(m, HumanMessage) and "The check found errors" in m.text
    ]
    assert "unsupported" in fix_request.text
    assert result["changeset"].edits == [GOOD_EDIT]


async def test_an_agent_that_never_fixes_its_changeset_fails_the_edit():
    with pytest.raises(GraphRecursionError):
        await _edit(_answer(BAD_EDIT))


async def test_an_agent_that_ends_without_a_changeset_is_asked_for_one():
    model = ScriptedChatModel(
        replies=[AIMessage("I've checked the edit and it passes."), _answer(GOOD_EDIT)]
    )

    result = await _graph(model).ainvoke(_input())

    assert any(
        isinstance(m, HumanMessage) and "no_changeset" in m.text
        for m in model.requests[-1]
    )
    assert result["changeset"].edits == [GOOD_EDIT]


async def test_page_fit_deletes_untouched_bullets_until_the_page_count_holds():
    result, _ = await _edit(_answer(NEW_BULLET))

    edits: list[AnyEdit] = result["changeset"].edits
    assert [edit.kind for edit in edits] == ["insert_item", "delete"]
    assert edits[1].path == "blocks/experience/items/lumen/bullets/latency"


@pytest.mark.parametrize(
    "insert",
    [
        InsertItem(
            kind="insert_item",
            parent="blocks/experience/items",
            after="bayu",
            item=PLATFORM_JOB,
        ),
        InsertBlock(
            kind="insert_block",
            after="experience",
            block=Experience(kind="experience", id="platform", items=[PLATFORM_JOB]),
        ),
    ],
)
async def test_page_fit_spares_the_bullets_the_changeset_inserted(
    insert: InsertItem | InsertBlock,
):
    result, _ = await _edit(_answer(insert))

    edits: list[AnyEdit] = result["changeset"].edits
    assert [edit.kind for edit in edits] == [insert.kind, "delete"]
    assert edits[1].path == "blocks/experience/items/lumen/bullets/latency"


async def test_clarify_pauses_the_edit_until_the_user_answers():
    graph = _graph(
        _model(_call("clarify", question="Which job?"), _answer(GOOD_EDIT)),
        checkpointer=InMemorySaver(),
    )
    run = {"configurable": {"thread_id": "t1"}}

    paused = await graph.ainvoke(_input(), run)
    done = await graph.ainvoke(Command(resume={"input": "Lumen Pay"}), run)

    assert [i.value["label"] for i in paused["__interrupt__"]] == ["Which job?"]
    assert done["changeset"].edits == [GOOD_EDIT]


async def test_page_fit_prints_with_the_files_from_the_input():
    sent: list[httpx.Request] = []
    graph = _graph(_model(_answer(GOOD_EDIT)), sent)

    await graph.ainvoke(_input(assets={"a" * 64: b"photo"}))

    assert sent
    assert all(
        json.loads(request.content)["assets"] == {"a" * 64: "cGhvdG8="}
        for request in sent
    )


async def test_a_document_never_printed_is_printed_first_for_its_page_count():
    sent: list[httpx.Request] = []
    graph = _graph(_model(_answer(GOOD_EDIT)), sent)
    printed = _input()

    result = await graph.ainvoke(printed)

    assert result["changeset"].edits == [GOOD_EDIT]
    assert len(sent) == 2
    assert json.loads(sent[0].content)["document"] == printed.document.model_dump(
        mode="json"
    )


async def test_a_failed_print_fails_the_edit_with_the_reason():
    graph = build_graph(
        _agent(_model(_answer(GOOD_EDIT))),
        ArtifactServiceClient(
            httpx.AsyncClient(
                transport=httpx.MockTransport(_fail),
                base_url="http://artifact-service",
            ),
        ),
    )

    with pytest.raises(ExecuteError, match="Couldn't print the edited document"):
        await graph.ainvoke(_input())


async def test_trace_records_each_check_round_and_the_agent_hash(
    make_settings, span_exporters
):
    instrument(
        make_settings(
            tracing_enabled=True,
            otlp_endpoint="http://collector:4318",
            instrumentations=["langchain"],
        )
    )

    await _edit(_answer(BAD_EDIT), _answer(GOOD_EDIT))
    tracing.shutdown_tracing()

    [exporter] = span_exporters
    rounds = [
        json.loads(span.attributes["check.errors"])
        for span in exporter.spans
        if "check.errors" in span.attributes
    ]
    assert [[e["rule"] for e in errors] for errors in rounds] == [["unsupported"], []]
    hashes = {
        json.loads(span.attributes["metadata"]).get("agent_hash")
        for span in exporter.spans
        if "metadata" in span.attributes
    }
    assert AGENT.hash in hashes
