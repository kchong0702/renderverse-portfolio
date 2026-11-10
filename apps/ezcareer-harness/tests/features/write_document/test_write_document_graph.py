import json
from functools import partial

import httpx
import pytest
from document_schema import (
    AnyDocument,
    AnyEdit,
    Bullet,
    Experience,
    InsertBlock,
    InsertItem,
    Job,
    RichValue,
)
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command
from pydantic import JsonValue, TypeAdapter
from pydantic_core import to_jsonable_python

from src.clients.artifact_service import ArtifactServiceClient
from src.core.errors import ExecuteError
from src.features.write_document.graph import build_graph
from src.features.write_document.types import EditInput, EditOutput
from src.infrastructure.observability import tracing
from src.infrastructure.observability.instrumentation import instrument
from tests.agents.career_consultant.test_career_consultant import (
    AGENT,
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    _agent,
    _model,
    _propose,
    _state,
)
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel

NEW_BULLET = InsertItem(
    kind="insert_item",
    parent="blocks/experience/items/lumen/bullets",
    after="latency",
    item=Bullet(
        id="k8s",
        text=RichValue(
            html="Ran production workloads on Kubernetes.", src=["fact:k8s"]
        ),
    ),
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
    model: ScriptedChatModel, sent: list[httpx.Request] | None = None
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
        InMemorySaver(),
    )


def _input() -> EditInput:
    return EditInput(
        messages=[HumanMessage("Mention my Kubernetes work")],
        document_id="doc-1",
        facts=_state()["facts"],
    )


def _fetched(**update: object) -> dict[str, JsonValue]:
    """What the client answers the document fetch with"""
    state = _state()
    return to_jsonable_python(
        {"document": state["document"], "lines": state["lines"]} | update
    )


async def _run(
    graph: CompiledStateGraph, fetched: dict[str, JsonValue] | None = None
) -> EditOutput:
    """Runs the edit and answers its document fetch"""
    run = {"configurable": {"thread_id": "t1"}}
    paused = await graph.ainvoke(_input(), run)
    assert [i.value for i in paused["__interrupt__"]] == [
        {"fetch": "document", "id": "doc-1"}
    ]
    return await graph.ainvoke(Command(resume=fetched or _fetched()), run)


async def _edit(*replies: AIMessage) -> tuple[EditOutput, ScriptedChatModel]:
    model = _model(*replies)
    return await _run(_graph(model)), model


async def test_a_free_reply_goes_out_without_a_changeset_or_a_print():
    sent: list[httpx.Request] = []
    model = _model(AIMessage("Your summary already leads with Kubernetes."))

    result = await _run(_graph(model, sent))

    assert result == {
        "reply": "Your summary already leads with Kubernetes.",
        "changeset": None,
    }
    assert sent == []
    [_, briefed] = model.requests[0]
    assert "<document>" in briefed.text
    assert briefed.text.endswith("The user says: Mention my Kubernetes work")


async def test_a_passing_changeset_goes_out_with_a_fresh_id_and_the_reply():
    result, _ = await _edit(
        _call("read_pdf_lines"),
        _call("read_profile_facts"),
        _call("read_file", file_path="/modify-career-documents/SKILL.md"),
        _propose(GOOD_EDIT),
        DONE,
    )

    assert result["reply"] == DONE.text
    assert result["changeset"].edits == [GOOD_EDIT]
    assert result["changeset"].id != "cs1"


async def test_errors_go_back_to_the_agent_and_only_the_fixed_changeset_is_kept():
    result, model = await _edit(_propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)

    first, second = [
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "propose_changeset"
    ]
    assert [error["rule"] for error in json.loads(first)] == ["unsupported"]
    assert second == "proposed"
    assert result["changeset"].edits == [GOOD_EDIT]


async def test_a_changeset_that_never_passes_is_never_kept():
    result, _ = await _edit(_propose(BAD_EDIT), DONE)

    assert result == {"reply": DONE.text, "changeset": None}


async def test_an_agent_that_never_stops_proposing_fails_the_edit():
    with pytest.raises(GraphRecursionError):
        await _edit(_propose(BAD_EDIT))


async def test_a_fetch_the_client_cannot_answer_fails_the_edit_with_its_reason():
    with pytest.raises(ExecuteError, match="No document doc-1"):
        await _run(_graph(_model(DONE)), {"error": "No document doc-1"})


async def test_page_fit_deletes_untouched_bullets_until_the_page_count_holds():
    result, _ = await _edit(_propose(NEW_BULLET), DONE)

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
            item=Job.model_validate(PLATFORM_JOB),
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
    result, _ = await _edit(_propose(insert), DONE)

    edits: list[AnyEdit] = result["changeset"].edits
    assert [edit.kind for edit in edits] == [insert.kind, "delete"]
    assert edits[1].path == "blocks/experience/items/lumen/bullets/latency"


async def test_clarify_pauses_the_edit_until_the_user_answers():
    graph = _graph(
        _model(_call("clarify", question="Which job?"), _propose(GOOD_EDIT), DONE)
    )
    run = {"configurable": {"thread_id": "t1"}}

    await graph.ainvoke(_input(), run)
    paused = await graph.ainvoke(Command(resume=_fetched()), run)
    done = await graph.ainvoke(Command(resume={"input": "Lumen Pay"}), run)

    assert [i.value["label"] for i in paused["__interrupt__"]] == ["Which job?"]
    assert done["changeset"].edits == [GOOD_EDIT]


async def test_page_fit_prints_the_document_first_with_the_fetched_files():
    sent: list[httpx.Request] = []

    await _run(
        _graph(_model(_propose(GOOD_EDIT), DONE), sent),
        _fetched(assets={"a" * 64: "cGhvdG8="}),
    )

    assert len(sent) == 2
    assert json.loads(sent[0].content)["document"] == _fetched()["document"]
    assert all(
        json.loads(request.content)["assets"] == {"a" * 64: "cGhvdG8="}
        for request in sent
    )


async def test_a_failed_print_fails_the_edit_with_the_reason():
    graph = build_graph(
        _agent(_model(_propose(GOOD_EDIT), DONE)),
        ArtifactServiceClient(
            httpx.AsyncClient(
                transport=httpx.MockTransport(_fail),
                base_url="http://artifact-service",
            ),
        ),
        InMemorySaver(),
    )

    with pytest.raises(ExecuteError, match="Couldn't print the edited document"):
        await _run(graph)


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

    await _edit(_propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)
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
