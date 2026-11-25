import json
from collections.abc import Callable
from functools import partial

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

from src.agents.career_consultant.page_fit import PageCountPreservationConfig
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
    **profile: object,
) -> Container:
    """A container whose career-consultant runs on model, prints with prints and has
    profile's fields in its profile.yaml"""
    container = Container()
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
    **profile: object,
) -> TestClient:
    return TestClient(create_app(_container(model, prints, **profile)))


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
    task: dict[str, JsonValue] | None,
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
                **_loaded(),
                "profile_facts": to_jsonable_python(_state()["profile_facts"]),
            }
        },
    ]


def _edit(client: TestClient) -> dict[str, JsonValue]:
    """Sends REQUEST with doc-1's content; returns the task"""
    return _send(client, _request())


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


def test_a_message_carries_its_document_and_the_proposal_is_a_changeset_artifact():
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
    [system, document, asked] = model.requests[0]
    assert _state()["document"].model_dump_json() not in system.text
    assert _state()["document"].model_dump_json() in document.text
    assert asked.text == REQUEST
    assert "propose_changeset" not in model.offered_tools[0]
    assert "propose_changeset" in model.offered_tools[1]


def test_a_message_without_a_document_fails_the_task_with_the_reason():
    model = _model(DONE)
    [text, data] = _request()
    del data["data"]["document"]

    failed = _send(_client(model), [text, data])

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    reason = failed["status"]["message"]["parts"][0]["text"]
    assert reason.startswith("Invalid input:")
    assert "document\n  Field required" in reason
    assert model.requests == []


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


def test_each_turn_stops_after_the_profiles_recursion_limit():
    model = _model(READ_SKILL, _propose(GOOD_EDIT), DONE)

    failed = _edit(_client(model, recursion_limit=2))

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "Ran out of steps"
    )


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


def test_page_fit_prints_the_document_it_was_sent_first():
    sent: list[httpx.Request] = []

    _edit(
        _client(
            _model(READ_SKILL, _propose(GOOD_EDIT), DONE), partial(_print, sent=sent)
        )
    )

    assert len(sent) == 2
    assert json.loads(sent[0].content)["document"] == _loaded()["document"]


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

    events = _stream(client, _request(), None)

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


def test_page_fit_deletes_at_most_the_profiles_max_bullet_trims():
    done = _edit(
        _client(
            _model(READ_SKILL, _propose(NEW_BULLET), DONE),
            page_count_preservation=PageCountPreservationConfig(max_bullet_trims=0),
        )
    )

    [proposed] = _changesets(done)
    assert proposed["changeset"]["edits"] == [NEW_BULLET.model_dump(mode="json")]


def test_with_page_count_preservation_disabled_the_changeset_is_never_printed():
    sent: list[httpx.Request] = []

    done = _edit(
        _client(
            _model(READ_SKILL, _propose(NEW_BULLET), DONE),
            partial(_print, sent=sent),
            page_count_preservation=PageCountPreservationConfig(enabled=False),
        )
    )

    [proposed] = _changesets(done)
    assert proposed["changeset"]["edits"] == [NEW_BULLET.model_dump(mode="json")]
    assert proposed["changeset"]["id"] != "cs1"
    assert proposed["changeset"]["agent"] == "career-consultant"
    assert sent == []
