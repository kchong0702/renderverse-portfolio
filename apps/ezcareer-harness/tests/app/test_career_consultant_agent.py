import json
from collections.abc import Callable
from functools import partial
from typing import Any

import httpx
import pytest
from dependency_injector import providers
from document_schema import (
    Bullet,
    Experience,
    InsertBlock,
    InsertItem,
    Job,
    RichValue,
)
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from src.app.app import create_app
from src.app.container import Container
from src.core.config import PageCountPreservationSettings, get_settings
from tests.agents.career_consultant.test_career_consultant import (
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    READ_SKILL,
    _fail,
    _loaded,
    _model,
    _print,
    _propose,
    _state,
)
from tests.agents.test_builder import _call
from tests.app import ops_api
from tests.conftest import ScriptedChatModel

REQUEST = "Mention my Kubernetes work in the queue bullet"
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


def _container(
    model: ScriptedChatModel,
    prints: Callable[[httpx.Request], httpx.Response] | None = None,
    page_count_preservation: PageCountPreservationSettings | None = None,
    **profile: object,
) -> Container:
    """A container whose career-consultant runs on model, prints with prints, uses any
    page_count_preservation given and has profile's fields in its profile.yaml"""
    container = Container()
    if page_count_preservation:
        container.settings.override(
            providers.Object(
                get_settings().model_copy(
                    update={"page_count_preservation": page_count_preservation}
                )
            )
        )
    agent = container.registry()["career-consultant"]
    container.registry.override(
        providers.Object(
            container.registry()
            | {
                agent.name: agent.model_copy(
                    update={"profile": agent.profile.model_copy(update=profile)}
                )
            }
        )
    )
    container.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(prints or partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    container.career_consultant.agent(model=model)
    return container


def _client(
    model: ScriptedChatModel,
    prints: Callable[[httpx.Request], httpx.Response] | None = None,
    page_count_preservation: PageCountPreservationSettings | None = None,
    **profile: object,
) -> TestClient:
    return TestClient(
        create_app(_container(model, prints, page_count_preservation, **profile))
    )


READ = _call("read_document")
PATH = "/ezcareer/a2a/career-consultant"
SAVED = {"changeset_id": "cs-saved"}


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
    **kwargs: Any,
) -> dict[str, JsonValue]:
    return ops_api.send(client, PATH, parts, task=task, **kwargs)


def _request() -> list[dict[str, JsonValue]]:
    return [
        {"text": REQUEST},
        {
            "data": {
                "document_id": "doc-1",
                "profile_facts": to_jsonable_python(_state()["profile_facts"]),
            }
        },
    ]


def _edit(
    client: TestClient,
    asked: list[JsonValue] | None = None,
    proposed: dict[str, JsonValue] = SAVED,
) -> dict[str, JsonValue]:
    """Sends REQUEST about doc-1, answering each read and proposal as ops-api does;
    returns the task"""
    return _send(
        client,
        _request(),
        answers={"read_document": _loaded(), "propose_changeset": proposed},
        asked=[] if asked is None else asked,
    )


def _proposals(asked: list[JsonValue]) -> list[dict[str, JsonValue]]:
    return [r for r in asked if r["execute_tool"] == "propose_changeset"]


def _changesets(task: dict[str, JsonValue]) -> list[dict[str, JsonValue]]:
    return [
        part["data"]
        for artifact in task.get("artifacts", [])
        if artifact["name"] == "changeset"
        for part in artifact["parts"]
    ]


def test_career_consultant_is_served_as_an_agent_with_the_containers_checkpointer():
    container = Container()
    container.career_consultant.agent(model=_model())

    card = TestClient(create_app(container)).get(
        "/ezcareer/a2a/career-consultant/.well-known/agent-card.json"
    )
    [served] = [
        e.graph for e in container.executables() if e.name == "career-consultant"
    ]

    assert card.json()["name"] == "career-consultant"
    assert served.checkpointer is container.checkpointer()
    assert container.career_consultant.agent().checkpointer is None


def test_a_message_names_its_document_which_is_read_then_the_proposal_is_saved():
    model = _model(READ, READ_SKILL, _propose(GOOD_EDIT), DONE)
    asked: list[JsonValue] = []

    done = _edit(_client(model), asked=asked)

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert asked[0] == {"execute_tool": "read_document", "document_id": "doc-1"}
    [request] = _proposals(asked)
    assert request["document_id"] == "doc-1"
    assert request["changeset"]["agent"] == "career-consultant"
    assert request["changeset"]["status"] == "pending"
    assert request["changeset"]["id"] != "cs1"
    assert request["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    assert _changesets(done) == [{"document_id": "doc-1", "changeset_id": "cs-saved"}]
    [reply] = [a for a in done["artifacts"] if a["name"] == "career-consultant"]
    assert reply["parts"][0]["text"] == DONE.text
    [system, sent] = model.requests[0]
    assert _state()["document"].model_dump_json() not in system.text
    assert sent.text.endswith(REQUEST)
    assert "propose_changeset" not in model.offered_tools[1]
    assert "propose_changeset" in model.offered_tools[2]


def test_the_editor_chat_carries_its_documents_thread_from_turn_to_turn():
    model = _model(DONE, AIMessage("Yes, the queue bullet does."))
    client = _client(model)
    [_, data] = _request()

    _send(client, _request(), context="doc-1-thread")
    _send(
        client, [{"text": "Does it mention Kubernetes?"}, data], context="doc-1-thread"
    )

    [_, first, reply, second] = model.requests[1]
    assert first.text.endswith(REQUEST)
    assert reply.text == DONE.text
    assert second.text.endswith("Does it mention Kubernetes?")


def test_a_proposal_ops_api_refuses_goes_back_to_the_agent():
    model = _model(READ, READ_SKILL, _propose(GOOD_EDIT), DONE)

    done = _edit(
        _client(model), proposed={"error": "The changeset no longer fits the draft"}
    )

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [report] = [
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "propose_changeset"
    ]
    assert json.loads(report) == [{"error": "The changeset no longer fits the draft"}]
    assert _changesets(done) == []


def test_a_message_without_a_document_id_fails_the_task_with_the_reason():
    model = _model(DONE)
    [text, data] = _request()
    del data["data"]["document_id"]

    failed = _send(_client(model), [text, data])

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    reason = failed["status"]["message"]["parts"][0]["text"]
    assert reason.startswith("Invalid input:")
    assert "document_id\n  Field required" in reason
    assert model.requests == []


def test_an_unclear_request_shows_the_user_a_widget_then_finishes():
    client = _client(
        _model(
            _call("clarify", question="Which job?"),
            READ,
            READ_SKILL,
            _propose(GOOD_EDIT),
            DONE,
        )
    )

    asked = _edit(client)
    done = _send(
        client,
        [{"data": {"input": "Lumen Pay"}}],
        task=asked,
        answers={"read_document": _loaded(), "propose_changeset": SAVED},
    )

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which job?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert _changesets(done) == [{"document_id": "doc-1", "changeset_id": "cs-saved"}]


def test_errors_go_back_to_the_agent_and_only_the_fixed_changeset_is_proposed():
    model = _model(READ, READ_SKILL, _propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)
    asked: list[JsonValue] = []

    done = _edit(_client(model), asked=asked)

    first, second = [
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "propose_changeset"
    ]
    assert [error["rule"] for error in json.loads(first)] == ["unknown_source"]
    assert second == "proposed"
    [request] = _proposals(asked)
    assert request["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    assert len(_changesets(done)) == 1


def test_a_changeset_that_never_passes_is_never_published_or_printed():
    sent: list[httpx.Request] = []

    done = _edit(
        _client(
            _model(READ, READ_SKILL, _propose(BAD_EDIT), DONE),
            partial(_print, sent=sent),
        )
    )

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert _changesets(done) == []
    assert sent == []


def test_an_agent_that_never_stops_proposing_fails_without_a_changeset():
    failed = _edit(_client(_model(READ, READ_SKILL, _propose(BAD_EDIT))))

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "Ran out of steps"
    )
    assert "artifacts" not in failed


def test_each_turn_stops_after_the_profiles_recursion_limit():
    model = _model(READ, READ_SKILL, _propose(GOOD_EDIT), DONE)

    failed = _edit(_client(model, recursion_limit=2))

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "Ran out of steps"
    )


def test_page_fit_deletes_untouched_bullets_until_the_page_count_holds():
    asked: list[JsonValue] = []

    _edit(_client(_model(READ, READ_SKILL, _propose(NEW_BULLET), DONE)), asked=asked)

    [proposed] = _proposals(asked)
    edits = proposed["changeset"]["edits"]
    assert [edit["kind"] for edit in edits] == ["insert_item", "delete"]
    assert edits[1]["path"] == "blocks/experience/items/lumen/bullets/latency"


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
def test_page_fit_spares_the_bullets_the_changeset_inserted(
    insert: InsertItem | InsertBlock,
):
    asked: list[JsonValue] = []

    _edit(_client(_model(READ, READ_SKILL, _propose(insert), DONE)), asked=asked)

    [proposed] = _proposals(asked)
    edits = proposed["changeset"]["edits"]
    assert [edit["kind"] for edit in edits] == [insert.kind, "delete"]
    assert edits[1]["path"] == "blocks/experience/items/lumen/bullets/latency"


def test_page_fit_prints_the_document_it_was_sent_first():
    sent: list[httpx.Request] = []

    _edit(
        _client(
            _model(READ, READ_SKILL, _propose(GOOD_EDIT), DONE),
            partial(_print, sent=sent),
        )
    )

    assert len(sent) == 2
    assert json.loads(sent[0].content)["document"] == _loaded()["document"]


def test_a_failed_print_fails_the_task_with_the_reason():
    failed = _edit(_client(_model(READ, READ_SKILL, _propose(GOOD_EDIT), DONE), _fail))

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "Couldn't print the edited document"
    )
    assert _changesets(failed) == []


def test_the_consultants_thinking_and_reply_stream_before_the_reply_artifact():
    client = _client(
        _model(
            AIMessage(
                [
                    {"type": "reasoning", "reasoning": "The summary names Kubernetes."},
                    {"type": "text", "text": "It already leads with Kubernetes."},
                ]
            )
        )
    )

    events = ops_api.stream(client, PATH, _request())

    assert [
        (
            e["artifactUpdate"]["artifact"]["name"],
            e["artifactUpdate"]["artifact"]["parts"][0],
        )
        for e in events
        if "artifactUpdate" in e
    ] == [
        ("thinking", {"text": "The summary names Kubernetes."}),
        ("text", {"text": "It already leads with Kubernetes."}),
        ("career-consultant", {"text": "It already leads with Kubernetes."}),
    ]
    assert events[-1]["statusUpdate"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_page_fit_deletes_at_most_max_bullet_trims():
    asked: list[JsonValue] = []

    _edit(
        _client(
            _model(READ, READ_SKILL, _propose(NEW_BULLET), DONE),
            page_count_preservation=PageCountPreservationSettings(max_bullet_trims=0),
        ),
        asked=asked,
    )

    [proposed] = _proposals(asked)
    assert proposed["changeset"]["edits"] == [NEW_BULLET.model_dump(mode="json")]


def test_with_page_count_preservation_disabled_the_changeset_is_never_printed():
    sent: list[httpx.Request] = []
    asked: list[JsonValue] = []

    _edit(
        _client(
            _model(READ, READ_SKILL, _propose(NEW_BULLET), DONE),
            partial(_print, sent=sent),
            page_count_preservation=PageCountPreservationSettings(enabled=False),
        ),
        asked=asked,
    )

    [proposed] = _proposals(asked)
    assert proposed["changeset"]["edits"] == [NEW_BULLET.model_dump(mode="json")]
    assert proposed["changeset"]["id"] != "cs1"
    assert proposed["changeset"]["agent"] == "career-consultant"
    assert sent == []
