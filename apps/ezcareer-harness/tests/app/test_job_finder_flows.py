import respx
from fastapi.testclient import TestClient

from src.app.app import create_app
from src.app.container import Container

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


def test_job_finder_graphs_keep_runs_in_the_containers_checkpointer():
    container = Container()

    graphs = [executable.graph for executable in container.executables()]

    assert [graph.checkpointer for graph in graphs] == [container.checkpointer()] * 2
