import json
from functools import partial
from typing import Any

import httpx
import respx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant import test_career_consultant as career_consultant
from tests.agents.career_consultant.test_career_consultant import _print
from tests.agents.career_director import test_tasks as tasks
from tests.agents.career_director.test_career_director import (
    BACKEND,
    REQUEST,
    _documents,
    _find,
    _model,
)
from tests.agents.career_director.test_update_profile import HEADLINE, READ_SKILL
from tests.agents.job_analyst.test_search_jobs import FOUND
from tests.agents.test_builder import _call
from tests.app import ops_api
from tests.app.test_ownership import _until
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job

PATH = "/ezcareer/a2a/career-director"
SAVED = {"changeset_id": "cs-saved"}


def _send(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
    context: str | None = None,
    **kwargs: Any,
) -> dict[str, JsonValue]:
    return ops_api.send(client, PATH, parts, task=task, context=context, **kwargs)


def _stream(
    client: TestClient,
    parts: list[dict[str, JsonValue]],
    task: dict[str, JsonValue] | None = None,
    **kwargs: Any,
) -> list[dict[str, JsonValue]]:
    """Every event SendStreamingMessage sends for one message and the history answer"""
    return ops_api.stream(
        client,
        PATH,
        parts,
        task={"id": task["taskId"], "contextId": task["contextId"]} if task else None,
        **kwargs,
    )


def _container(
    analyst: ScriptedChatModel,
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
    container.job_analyst.agent(model=analyst)
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
                    "profile_facts": analyse_job.INPUT["profile_facts"],
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
    analyst = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("search_jobs", query="backend engineer", remote_only=True),
            _call("RankedJobs", jobs=[]),
        ]
    )
    director = _model(_call("find_jobs"), AIMessage("No jobs fit yet."))
    client = TestClient(create_app(_container(analyst, _model(), director)))

    asked = _send(
        client,
        [
            {"text": "Find me remote jobs"},
            {
                "data": {
                    "profile_facts": analyse_job.INPUT["profile_facts"],
                    "preferences": {"work_modes": ["remote"]},
                }
            },
        ],
    )
    done = _send(client, [{"data": FOUND}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    [request] = asked["status"]["message"]["parts"]
    assert (request["data"]["execute_tool"], request["data"]["remote_only"]) == (
        "job_search",
        True,
    )
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [report] = [m for m in director.requests[1] if isinstance(m, ToolMessage)]
    assert json.loads(report.text) == {"jobs": []}
    assert '"work_modes":["remote"]' in analyst.requests[0][-1].text


def test_career_director_hears_why_find_jobs_could_not_search():
    reason = "Connect JSearch in Settings to search for jobs"
    analyst = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            _call("search_jobs", query="backend engineer"),
            _call("RankedJobs", jobs=[]),
        ]
    )
    director = _model(_call("find_jobs"), AIMessage("Connect JSearch first."))
    client = TestClient(create_app(_container(analyst, _model(), director)))

    asked = _send(
        client,
        [
            {"text": "Find me jobs"},
            {
                "data": {
                    "profile_facts": analyse_job.INPUT["profile_facts"],
                    "preferences": {},
                }
            },
        ],
    )
    done = _send(client, [{"data": {"error": reason}}], task=asked)

    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [report] = [m for m in director.requests[1] if isinstance(m, ToolMessage)]
    assert (report.status, report.text) == ("error", reason)


def _director_request() -> list[dict[str, JsonValue]]:
    return [
        {"text": REQUEST},
        {
            "data": {
                "profile_facts": to_jsonable_python(
                    career_consultant._state()["profile_facts"]
                ),
                "preferences": {},
            }
        },
    ]


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
    assert [p["data"] for p in asked["status"]["message"]["parts"]] == [
        {
            "label": "Which résumé?",
            "choose": "document",
            "kind": "resume",
            "submit_btn": "Send",
        }
    ]


def test_a_picked_document_is_not_replayed_into_a_later_request_of_the_turn():
    director = _model(
        _call("choose_document", question="Which résumé?", kind="resume"),
        _find(name="Backend résumé", kind="resume"),
        AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "find_documents",
                    "args": {"name": "Frontend résumé"},
                    "id": "call-find-again",
                }
            ],
        ),
    )
    client = TestClient(create_app(_container(_model(), _model(), director)))

    asked = _send(client, _director_request())
    finding = _send(client, [{"data": {"input": "Backend résumé"}}], task=asked)
    [request] = finding["status"]["message"]["parts"]
    again = _send(
        client,
        [{"data": _documents(BACKEND), "metadata": request["metadata"]}],
        task=finding,
    )

    assert again["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert [p["data"] for p in again["status"]["message"]["parts"]] == [
        {"execute_tool": "documents", "name": "Frontend résumé", "kind": None}
    ]


def _steps(events: list[dict[str, JsonValue]]) -> list[dict[str, JsonValue]]:
    return [
        e["statusUpdate"]["status"]["message"]["parts"][0]["data"]["step"]
        for e in events
        if "step"
        in e.get("statusUpdate", {})
        .get("status", {})
        .get("message", {"parts": [{}]})["parts"][0]
        .get("data", {})
    ]


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
            {
                "data": {
                    "profile_facts": analyse_job.INPUT["profile_facts"],
                    "preferences": {},
                }
            },
        ],
    )

    steps = _steps(events)
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
    assert [
        (usage["agent"], usage["node"], usage["provider"], usage["model"])
        for e in events
        for part in e.get("statusUpdate", {})
        .get("status", {})
        .get("message", {"parts": []})["parts"]
        if "usage" in (usage := part.get("data", {})) and (usage := usage["usage"])
    ] == [
        ("career-director", "model", "openai", "gpt-6-luna"),
        ("job-analyst", "model", "glm", "glm-5.3"),
        ("career-director", "model", "openai", "gpt-6-luna"),
    ]


def test_a_profile_update_waits_for_the_users_decision_and_saves_once_approved():
    director = _model(
        READ_SKILL,
        _call("update_profile", edits=[HEADLINE]),
        AIMessage("I saved your headline."),
    )
    client = TestClient(create_app(_container(_model(), _model(), director)))

    reviewing = _stream(client, _director_request())
    task = reviewing[-1]["statusUpdate"]
    saving = _stream(
        client, [{"data": {"decisions": [{"type": "approve"}]}}], task=task
    )
    done = _stream(client, [{"data": {"saved": 1}}], task=task)

    assert task["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    [review] = task["status"]["message"]["parts"]
    assert review["data"]["action_requests"][0]["name"] == "update_profile"
    assert review["data"]["action_requests"][0]["args"] == {"edits": [HEADLINE]}
    assert review["data"]["review_configs"] == [
        {"action_name": "update_profile", "allowed_decisions": ["approve", "reject"]}
    ]
    assert [
        p["data"] for p in saving[-1]["statusUpdate"]["status"]["message"]["parts"]
    ] == [{"execute_tool": "profile_update", "edits": [HEADLINE]}]
    assert [
        (
            e["artifactUpdate"]["artifact"]["name"],
            e["artifactUpdate"]["artifact"]["parts"],
        )
        for e in done
        if "artifactUpdate" in e
    ] == [
        ("profile_updated", [{"data": {"saved": 1}}]),
        ("text", [{"text": "I saved your headline."}]),
        ("career-director", [{"text": "I saved your headline."}]),
    ]
    assert done[-1]["statusUpdate"]["status"]["state"] == "TASK_STATE_COMPLETED"


def test_parallel_tasks_stream_one_step_and_changeset_each_and_only_the_directors_text():
    letter = tasks._edits("letter")
    director = _model(
        tasks._calls(
            tasks._assign("backend", "doc-1", tasks.BACKEND_TASK),
            tasks._assign("letter", "doc-2", tasks.LETTER_TASK),
            tasks._assign("again", "doc-1", "Shorten the summary"),
        ),
        tasks.DONE,
    )
    consultant = tasks.TaskModel(
        scripts={
            tasks.BACKEND_TASK: tasks._edits("backend"),
            tasks.LETTER_TASK: [
                *letter[:2],
                tasks._calls(("letter-reread", "read_document", {})),
                *letter[2:],
            ],
        }
    )
    client = TestClient(create_app(_container(_model(), consultant, director)))

    events = _stream(
        client,
        _director_request(),
        answers={
            "read_document": career_consultant._loaded(),
            "propose_changeset": SAVED,
        },
    )

    steps = [
        (s["id"], s["status"], s["detail"])
        for s in _steps(events)
        if s["name"] == "assign_career_consultant_task"
    ]
    assert [s for s in steps if s[0] == "backend"] == [
        ("backend", "running", None),
        ("backend", "waiting", None),
        ("backend", "running", None),
        ("backend", "waiting", None),
        ("backend", "running", None),
        ("backend", "done", "Backend résumé"),
    ]
    assert [s for s in steps if s[0] == "again"] == [
        ("again", "running", None),
        ("again", "failed", None),
    ]
    assert steps.index(("backend", "done", "Backend résumé")) < steps.index(
        ("letter", "done", "Backend résumé")
    )
    assert steps[-1] == ("letter", "done", "Backend résumé")
    assert [
        (
            e["artifactUpdate"]["artifact"]["name"],
            e["artifactUpdate"]["artifact"]["parts"],
        )
        for e in events
        if "artifactUpdate" in e
    ] == [
        ("changeset", [{"data": {"document_id": "doc-1", **SAVED}}]),
        ("changeset", [{"data": {"document_id": "doc-2", **SAVED}}]),
        ("text", [{"text": tasks.DONE.text}]),
        ("career-director", [{"text": tasks.DONE.text}]),
    ]


def test_stopping_a_run_cancels_every_task_it_runs():
    director = _model(
        tasks._calls(
            tasks._assign("backend", "doc-1", tasks.BACKEND_TASK),
            tasks._assign("letter", "doc-2", tasks.LETTER_TASK),
        )
    )
    consultant = tasks.TaskModel(hang={tasks.BACKEND_TASK, tasks.LETTER_TASK})
    with TestClient(create_app(_container(_model(), consultant, director))) as client:
        started = client.post(
            PATH,
            headers={"A2A-Version": "1.0"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "SendMessage",
                "params": {
                    "message": {
                        "messageId": "m-stop",
                        "role": "ROLE_USER",
                        "parts": _director_request(),
                        "metadata": {"created_at": ops_api.SENT_AT},
                    },
                    "configuration": {"returnImmediately": True},
                },
            },
        ).json()["result"]["task"]
        _until(lambda: len(consultant.log) == 2, "started both tasks")
        cancelled = client.post(
            PATH,
            headers={"A2A-Version": "1.0"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "CancelTask",
                "params": {"id": started["id"]},
            },
        ).json()["result"]
        _until(lambda: len(consultant.log) == 4, "cancelled both tasks")

    assert cancelled["status"]["state"] == "TASK_STATE_CANCELED"
    assert sorted(consultant.log) == sorted(
        f"{what} {task}"
        for what in ("waiting", "cancelled")
        for task in (tasks.BACKEND_TASK, tasks.LETTER_TASK)
    )


def test_a_tasks_question_reaches_the_user_and_their_bare_answer_resumes_it():
    director = _model(
        tasks._calls(tasks._assign("backend", "doc-1", tasks.BACKEND_TASK)),
        tasks.DONE,
    )
    consultant = tasks.TaskModel(
        scripts={
            tasks.BACKEND_TASK: [
                tasks._calls(("ask", "clarify", {"question": "Which bullet?"})),
                AIMessage("I'll name it in the queue bullet."),
            ]
        }
    )
    client = TestClient(create_app(_container(_model(), consultant, director)))

    asked = _send(client, _director_request())
    done = _send(client, [{"text": "The queue one"}], task=asked)

    assert asked["status"]["message"]["parts"][0]["data"]["label"] == "Which bullet?"
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    [answer] = [
        m.text
        for m in consultant.requests[-1]
        if isinstance(m, ToolMessage) and m.name == "clarify"
    ]
    assert answer == "The queue one"
    [report] = [
        m.text
        for m in director.requests[-1]
        if isinstance(m, ToolMessage) and m.tool_call_id == "backend"
    ]
    assert report == "I'll name it in the queue bullet."
