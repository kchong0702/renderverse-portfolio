import json
from collections.abc import Callable
from functools import partial

import httpx
import pytest
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
) -> Container:
    container = Container()
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
) -> TestClient:
    return TestClient(create_app(_container(model, prints)))


def _message(
    parts: list[dict[str, JsonValue]], task: dict[str, JsonValue] | None
) -> dict[str, JsonValue]:
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    return message


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    response = client.post(
        "/ezcareer/a2a/career-consultant",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": _message(parts, task)},
        },
    )
    return response.json()["result"]["task"]


def _stream(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue],
) -> list[dict[str, JsonValue]]:
    """Every event SendStreamingMessage sends for one message"""
    with client.stream(
        "POST",
        "/ezcareer/a2a/career-consultant",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendStreamingMessage",
            "params": {"message": _message(parts, task)},
        },
    ) as response:
        return [
            json.loads(line.removeprefix("data: "))["result"]
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]


def _request() -> list[dict[str, JsonValue]]:
    return [
        {"text": REQUEST},
        {
            "data": {
                "document_id": "doc-1",
                "facts": to_jsonable_python(_state()["facts"]),
            }
        },
    ]


def _edit(
    client: TestClient, loaded: dict[str, JsonValue] | None = None
) -> dict[str, JsonValue]:
    """Sends REQUEST about doc-1 and answers the document tool; returns the task"""
    asked = _send(client, _request())
    assert [p["data"] for p in asked["status"]["message"]["parts"]] == [
        {"execute_tool": "document", "id": "doc-1"}
    ]
    return _send(client, [{"data": loaded or _loaded()}], task=asked)


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


def test_a_message_loads_its_document_then_the_proposal_is_a_changeset_artifact():
    model = _model(READ_SKILL, _propose(GOOD_EDIT), DONE)

    done = _edit(_client(model))

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [proposed] = _changesets(done)
    assert proposed["document_id"] == "doc-1"
    assert proposed["changeset"]["agent"] == "career-consultant"
    assert proposed["changeset"]["status"] == "pending"
    assert proposed["changeset"]["id"] != "cs1"
    assert proposed["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    [reply] = [a for a in done["artifacts"] if a["name"] == "career-consultant"]
    assert reply["parts"][0]["text"] == DONE.text
    [system, asked] = model.requests[0]
    assert _state()["document"].model_dump_json() in system.text
    assert asked.text == REQUEST
    assert "propose_changeset" not in model.offered_tools[0]
    assert "propose_changeset" in model.offered_tools[1]


@pytest.mark.parametrize(
    ("answer", "reason"),
    [
        ({"error": "No document doc-1"}, "No document doc-1"),
        ({"document": "not a document"}, "The document didn't load"),
    ],
)
def test_a_document_ops_cannot_load_fails_the_task_with_the_reason(
    answer: dict[str, JsonValue], reason: str
):
    failed = _edit(_client(_model(DONE)), answer)

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(reason)
    assert "artifacts" not in failed


def test_an_unclear_request_shows_the_user_a_widget_then_finishes():
    client = _client(
        _model(
            _call("clarify", question="Which job?"),
            READ_SKILL,
            _propose(GOOD_EDIT),
            DONE,
        )
    )

    asked = _edit(client)
    done = _send(client, [{"data": {"input": "Lumen Pay"}}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which job?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [proposed] = _changesets(done)
    assert proposed["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]


def test_errors_go_back_to_the_agent_and_only_the_fixed_changeset_is_published():
    model = _model(READ_SKILL, _propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)

    done = _edit(_client(model))

    first, second = [
        m.text
        for m in model.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "propose_changeset"
    ]
    assert [error["rule"] for error in json.loads(first)] == ["unknown_source"]
    assert second == "proposed"
    [proposed] = _changesets(done)
    assert proposed["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]


def test_a_changeset_that_never_passes_is_never_published_or_printed():
    sent: list[httpx.Request] = []

    done = _edit(
        _client(
            _model(READ_SKILL, _propose(BAD_EDIT), DONE), partial(_print, sent=sent)
        )
    )

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert _changesets(done) == []
    assert sent == []


def test_an_agent_that_never_stops_proposing_fails_without_a_changeset():
    failed = _edit(_client(_model(READ_SKILL, _propose(BAD_EDIT))))

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "Ran out of steps"
    )
    assert "artifacts" not in failed


def test_page_fit_deletes_untouched_bullets_until_the_page_count_holds():
    done = _edit(_client(_model(READ_SKILL, _propose(NEW_BULLET), DONE)))

    [proposed] = _changesets(done)
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
    done = _edit(_client(_model(READ_SKILL, _propose(insert), DONE)))

    [proposed] = _changesets(done)
    edits = proposed["changeset"]["edits"]
    assert [edit["kind"] for edit in edits] == [insert.kind, "delete"]
    assert edits[1]["path"] == "blocks/experience/items/lumen/bullets/latency"


def test_page_fit_prints_the_document_first_with_the_loaded_files():
    sent: list[httpx.Request] = []

    _edit(
        _client(
            _model(READ_SKILL, _propose(GOOD_EDIT), DONE), partial(_print, sent=sent)
        ),
        _loaded(assets={"a" * 64: "cGhvdG8="}),
    )

    assert len(sent) == 2
    assert json.loads(sent[0].content)["document"] == _loaded()["document"]
    assert all(
        json.loads(request.content)["assets"] == {"a" * 64: "cGhvdG8="}
        for request in sent
    )


def test_a_failed_print_fails_the_task_with_the_reason():
    failed = _edit(_client(_model(READ_SKILL, _propose(GOOD_EDIT), DONE), _fail))

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

    asked = _send(client, _request())
    events = _stream(client, [{"data": _loaded()}], asked)

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
