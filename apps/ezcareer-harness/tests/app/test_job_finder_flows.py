import respx
from fastapi.testclient import TestClient

from src.app.app import create_app
from src.app.container import Container
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job

URL = "https://jobs.example.com/gone"


def _send(client: TestClient, path: str, data: dict) -> dict:
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
                    "parts": [{"data": data}],
                }
            },
        },
    )
    return response.json()["result"]["task"]


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
        client, "/ezcareer/a2a/analyse-job", {"url": URL, "profile": {"facts": []}}
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"][0]["text"].startswith(
        "Couldn't fetch the posting"
    )


@respx.mock
def test_a_served_analysis_completes_through_the_containers_checkpointer():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    container = Container()
    container.job_finder(
        model=ScriptedChatModel(
            replies=[analyse_job._answer("5+ years of Python in production")]
        )
    )

    task = _send(
        TestClient(create_app(container)),
        "/ezcareer/a2a/analyse-job",
        analyse_job.INPUT,
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["data"]["analysis"]["fit"] == 67


def test_job_finder_workflows_keep_runs_in_the_containers_checkpointer():
    container = Container()

    graphs = [e.graph for e in container.executables() if e.kind == "workflow"]

    assert [graph.checkpointer for graph in graphs] == [container.checkpointer()] * 2


def test_find_jobs_gets_its_sources_from_the_containers_one_factory():
    container = Container()

    factory = container.job_sources()

    assert container.job_sources() is factory
    assert factory.create("jsearch") is factory.create("jsearch")


def test_job_finder_is_served_as_an_agent_beside_its_workflows():
    client = TestClient(create_app())

    card = client.get("/ezcareer/a2a/job-finder/.well-known/agent-card.json")

    assert card.json()["name"] == "job-finder"
    assert [e.kind for e in Container().executables()] == [
        "agent",
        "workflow",
        "workflow",
    ]


def test_both_workflows_run_on_the_containers_one_job_finder():
    container = Container()

    analyse, find = container.analyse_job_graph(), container.find_jobs_graph()

    assert container.job_finder() is container.job_finder()
    assert analyse is container.analyse_job_graph()
    assert find is container.find_jobs_graph()
