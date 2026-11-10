import json
from functools import partial

import httpx
import respx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant import test_career_consultant as career_consultant
from tests.agents.career_director.test_career_director import (
    BACKEND,
    REQUEST,
    _find,
    _model,
)
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job
from tests.features.write_document.test_write_document_graph import _fetched, _print


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
) -> dict[str, JsonValue]:
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    response = client.post(
        "/ezcareer/a2a/career-director",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {"message": message},
        },
    )
    return response.json()["result"]["task"]


def _stream(
    client: TestClient, parts: list[dict[str, JsonValue]]
) -> list[dict[str, JsonValue]]:
    """Every event SendStreamingMessage sends for one message"""
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    with client.stream(
        "POST",
        "/ezcareer/a2a/career-director",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendStreamingMessage",
            "params": {"message": message},
        },
    ) as response:
        return [
            json.loads(line.removeprefix("data: "))["result"]
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]


def _container(
    finder: ScriptedChatModel,
    consultant: ScriptedChatModel,
    director: ScriptedChatModel,
) -> Container:
    container = Container()
    container.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    container.job_finder.agent(model=finder)
    container.career_consultant.agent(model=consultant)
    container.career_director.agent(model=director)
    return container


def test_career_director_is_served_as_an_agent_with_the_containers_checkpointer():
    container = _container(_model(), _model(), _model())

    card = TestClient(create_app(container)).get(
        "/ezcareer/a2a/career-director/.well-known/agent-card.json"
    )
    [served] = [e.graph for e in container.executables() if e.name == "career-director"]

    assert card.json()["name"] == "career-director"
    assert served.checkpointer is container.checkpointer()
    assert container.career_director.agent().checkpointer is None


@respx.mock
def test_career_director_analyses_the_posting_at_a_url_through_analyse_job():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    director = _model(
        _call("analyse_job", url=analyse_job.URL), AIMessage("It fits 67%.")
    )
    container = _container(
        ScriptedChatModel(
            replies=[analyse_job._answer("5+ years of Python in production")]
        ),
        _model(),
        director,
    )

    task = _send(
        TestClient(create_app(container)),
        [
            {"text": f"How well do I fit {analyse_job.URL}?"},
            {
                "data": {
                    "facts": analyse_job.INPUT["facts"],
                    "preferences": analyse_job.INPUT["preferences"],
                }
            },
        ],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "career-director"]
    assert reply["parts"][0]["text"] == "It fits 67%."
    [report] = [m for m in director.requests[1] if isinstance(m, ToolMessage)]
    assert '"fit":67' in report.text


def test_career_director_finds_jobs_for_the_users_preferences_through_find_jobs():
    finder = ScriptedChatModel(replies=[_call("RankedJobs", jobs=[])])
    director = _model(_call("find_jobs"), AIMessage("No jobs fit yet."))
    container = _container(finder, _model(), director)

    task = _send(
        TestClient(create_app(container)),
        [
            {"text": "Find me remote jobs"},
            {"data": {"facts": [], "preferences": {"work_modes": ["remote"]}}},
        ],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [report] = [m for m in director.requests[1] if isinstance(m, ToolMessage)]
    assert json.loads(report.text) == {"jobs": []}
    assert '"work_modes":["remote"]' in finder.requests[0][-1].text


def _director_request() -> list[dict[str, JsonValue]]:
    return [
        {"text": REQUEST},
        {
            "data": {
                "facts": to_jsonable_python(career_consultant._state()["facts"]),
                "preferences": {},
            }
        },
    ]


def test_a_found_document_is_edited_and_its_changeset_is_published_as_an_artifact():
    consultant = career_consultant._model(
        career_consultant._propose(career_consultant.GOOD_EDIT),
        career_consultant.DONE,
    )
    director = _model(
        _find(name="backend résumé", kind="resume"),
        _call("edit_document", document_id="doc-1", request=REQUEST),
        AIMessage("I proposed one edit."),
    )
    client = TestClient(create_app(_container(_model(), consultant, director)))

    finding = _send(client, _director_request())
    fetching = _send(client, [{"data": {"documents": [BACKEND]}}], task=finding)
    done = _send(client, [{"data": _fetched()}], task=fetching)

    assert [
        (task["status"]["state"], task["status"]["message"]["parts"])
        for task in (finding, fetching)
    ] == [
        (
            "TASK_STATE_INPUT_REQUIRED",
            [
                {
                    "data": {
                        "fetch": "documents",
                        "name": "backend résumé",
                        "kind": "resume",
                    }
                }
            ],
        ),
        (
            "TASK_STATE_INPUT_REQUIRED",
            [{"data": {"fetch": "document", "id": "doc-1"}}],
        ),
    ]
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [changeset] = [a for a in done["artifacts"] if a["name"] == "changeset"]
    [part] = changeset["parts"]
    assert part["data"]["document_id"] == "doc-1"
    assert part["data"]["changeset"]["edits"] == [
        career_consultant.GOOD_EDIT.model_dump(mode="json")
    ]
    [reply] = [a for a in done["artifacts"] if a["name"] == "career-director"]
    assert reply["parts"][0]["text"] == "I proposed one edit."


def test_a_documents_answer_ops_api_cannot_read_fails_the_turn():
    director = _model(_find(name="backend résumé", kind="resume"))
    client = TestClient(create_app(_container(_model(), _model(), director)))

    finding = _send(client, _director_request())
    failed = _send(client, [{"data": {"documents": "not a list"}}], task=finding)

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"][0]["text"].startswith(
        "The documents didn't load"
    )


def test_an_unclear_document_shows_the_user_a_document_picker():
    director = _model(
        _call("choose_document", question="Which résumé?", kind="resume"),
        AIMessage("Which one?"),
    )
    client = TestClient(create_app(_container(_model(), _model(), director)))

    asked = _send(client, _director_request())

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"] == [
        {
            "data": {
                "label": "Which résumé?",
                "choose": "document",
                "kind": "resume",
                "submit_btn": "Send",
            }
        }
    ]


def test_a_workflows_question_reaches_the_user_and_their_answer_finishes_the_turn():
    consultant = career_consultant._model(
        _call("clarify", question="Which bullet?"),
        career_consultant._propose(career_consultant.GOOD_EDIT),
        career_consultant.DONE,
    )
    director = _model(
        _call("edit_document", document_id="doc-1", request=REQUEST),
        AIMessage("I proposed one edit."),
    )
    client = TestClient(create_app(_container(_model(), consultant, director)))

    fetching = _send(client, _director_request())
    asked = _send(client, [{"data": _fetched()}], task=fetching)
    done = _send(client, [{"data": {"input": "The queue one"}}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which bullet?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in done["artifacts"] if a["name"] == "career-director"]
    assert reply["parts"][0]["text"] == "I proposed one edit."
    [answer] = [
        m.text
        for m in consultant.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "clarify"
    ]
    assert answer == "The queue one"
    [report] = [m for m in director.requests[-1] if isinstance(m, ToolMessage)]
    assert report.text.startswith(career_consultant.DONE.text)
    assert len(director.requests) == 2


@respx.mock
def test_career_director_streams_its_thinking_steps_and_reply():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    director = _model(
        _call("analyse_job", url=analyse_job.URL),
        AIMessage(
            [
                {"type": "reasoning", "reasoning": "The posting asks for Python."},
                {"type": "text", "text": "It fits 67%."},
            ]
        ),
    )
    container = _container(
        ScriptedChatModel(
            replies=[analyse_job._answer("5+ years of Python in production")]
        ),
        _model(),
        director,
    )

    events = _stream(
        TestClient(create_app(container)),
        [
            {"text": f"How well do I fit {analyse_job.URL}?"},
            {"data": {"facts": analyse_job.INPUT["facts"], "preferences": {}}},
        ],
    )

    steps = [
        e["statusUpdate"]["status"]["message"]["parts"][0]["data"]["step"]
        for e in events
        if "message" in e.get("statusUpdate", {}).get("status", {})
    ]
    call = steps[0]["id"]
    assert [(s["name"], s["status"], s["parent"]) for s in steps] == [
        ("analyse_job", "running", None),
        ("fetch", "running", call),
        ("fetch", "done", call),
        ("agent", "running", call),
        ("agent", "done", call),
        ("check", "running", call),
        ("check", "done", call),
        ("output", "running", call),
        ("output", "done", call),
        ("analyse_job", "done", None),
    ]
    assert [
        (
            e["artifactUpdate"]["artifact"]["name"],
            e["artifactUpdate"]["artifact"]["parts"][0]["text"],
        )
        for e in events
        if "artifactUpdate" in e
    ] == [
        ("thinking", "The posting asks for Python."),
        ("text", "It fits 67%."),
        ("career-director", "It fits 67%."),
    ]
    assert events[-1]["statusUpdate"]["status"]["state"] == "TASK_STATE_COMPLETED"
