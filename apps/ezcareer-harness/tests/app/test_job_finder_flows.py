import io
import json
import logging
from typing import override

import pytest
import respx
import structlog
from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import providers
from fastapi.testclient import TestClient
from google.protobuf.json_format import MessageToJson

from src.app.app import create_app
from src.app.container import Container
from src.core.config import reload_settings
from src.infrastructure.observability import logging as obs_logging
from tests.agents.job_finder.test_search_jobs import RESPONSE
from tests.agents.job_finder.test_search_jobs import URL as JSEARCH
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job

URL = "https://jobs.example.com/gone"
USER_KEY = "user-rapidapi-key-0123456789"


def _send(
    client: TestClient, path: str, parts: list[dict], metadata: dict | None = None
) -> dict:
    response = client.post(
        path,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m1",
                    "role": "ROLE_USER",
                    "parts": parts,
                },
                **({"metadata": metadata} if metadata else {}),
            },
        },
    )
    return response.json()["result"]["task"]


@pytest.fixture
def debug_logs(make_settings):
    """Every log line at DEBUG, into a private buffer, restoring global logging after"""
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    buffer = io.StringIO()
    obs_logging.configure_logging(make_settings(log_level="DEBUG"), force=True)
    root.handlers[-1].setStream(buffer)
    yield buffer
    root.handlers[:] = handlers
    root.setLevel(level)
    obs_logging._configured = False
    structlog.reset_defaults()


@respx.mock
def test_jsearch_only_metadata_runs_on_its_key_and_never_logs_or_stores_it(
    isolate_env, debug_logs
):
    reload_settings()
    route = respx.get(JSEARCH).respond(200, text=RESPONSE)
    saved: list[str] = []

    class RecordingStore(InMemoryTaskStore):
        @override
        async def save(self, task, context) -> None:
            saved.append(MessageToJson(task))
            await super().save(task, context)

    container = Container()
    container.task_store.override(providers.Singleton(RecordingStore))
    container.job_finder.agent(
        model=ScriptedChatModel(
            replies=[
                _call("read_file", file_path="/search-jobs/SKILL.md"),
                _call("search_jobs", query="backend engineer"),
                _call("RankedJobs", jobs=[]),
            ]
        )
    )

    task = _send(
        TestClient(create_app(container)),
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": analyse_job.INPUT["facts"]}}],
        metadata={"jsearch": {"api_key": USER_KEY}},
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert route.calls.last.request.headers["X-RapidAPI-Key"] == USER_KEY
    assert saved
    assert USER_KEY not in json.dumps(task) + "".join(saved)
    assert "find-jobs" in debug_logs.getvalue()
    assert USER_KEY not in debug_logs.getvalue()
    reload_settings()


def test_metadata_that_does_not_validate_fails_without_echoing_the_key():
    task = _send(
        TestClient(create_app()),
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": []}}],
        metadata={"jsearch": {"api_key": USER_KEY, "extra": True}},
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert USER_KEY not in json.dumps(task)


def test_job_finder_flows_have_agent_cards():
    client = TestClient(create_app())

    for name in ("analyse-job", "find-jobs"):
        card = client.get(f"/ezcareer/a2a/{name}/.well-known/agent-card.json")
        assert card.json()["name"] == name


@respx.mock
def test_a_posting_that_cannot_be_fetched_fails_the_task_with_the_reason():
    respx.get(URL).respond(404)
    client = TestClient(create_app())

    task = _send(
        client, "/ezcareer/a2a/analyse-job", [{"data": {"url": URL, "facts": []}}]
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"][0]["text"].startswith(
        "Couldn't fetch the posting"
    )


@respx.mock
def test_a_served_analysis_completes_through_the_containers_checkpointer():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    model = ScriptedChatModel(
        replies=[analyse_job._answer("5+ years of Python in production")]
    )
    container = Container()
    container.job_finder.agent(model=model)

    task = _send(
        TestClient(create_app(container)),
        "/ezcareer/a2a/analyse-job",
        [{"text": "Focus on visa"}, {"data": analyse_job.INPUT}],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["data"]["analysis"]["fit"] == 67
    assert model.requests[0][1].text == "Focus on visa"
    assert "<posting untrusted>" in model.requests[0][2].text


def test_find_jobs_gets_its_sources_from_the_containers_one_factory():
    container = Container()

    factory = container.clients.job_sources()

    assert container.clients.job_sources() is factory
    assert factory.create("jsearch") is factory.create("jsearch")


def test_job_finder_is_served_as_an_agent_with_the_containers_checkpointer():
    container = Container()
    container.job_finder.agent(model=ScriptedChatModel(replies=[]))

    card = TestClient(create_app(container)).get(
        "/ezcareer/a2a/job-finder/.well-known/agent-card.json"
    )
    [served] = [e.graph for e in container.executables() if e.name == "job-finder"]

    assert card.json()["name"] == "job-finder"
    assert served.checkpointer is container.checkpointer()
    assert container.job_finder.agent().checkpointer is None


@respx.mock
async def test_both_workflows_run_on_the_containers_one_job_finder():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    model = ScriptedChatModel(
        replies=[
            analyse_job._answer("5+ years of Python in production"),
            _call("RankedJobs", jobs=[]),
        ]
    )
    container = Container()
    container.job_finder.agent(model=model)
    graphs = {e.name: e.graph for e in container.executables()}

    analysed = await graphs["analyse-job"].ainvoke(
        analyse_job.INPUT, {"configurable": {"thread_id": "analyse"}}
    )
    found = await graphs["find-jobs"].ainvoke(
        {"facts": []}, {"configurable": {"thread_id": "find"}}
    )

    assert analysed["analysis"].fit == 67
    assert found["jobs"] == []
    assert "<posting untrusted>" in model.requests[0][1].text
    assert "Find jobs for me" in model.requests[1][1].text
