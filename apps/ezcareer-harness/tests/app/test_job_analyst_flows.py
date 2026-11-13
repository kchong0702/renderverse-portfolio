import json

import respx
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage

from src.app.app import create_app
from src.app.container import Container
from tests.agents.job_analyst.test_search_jobs import FOUND
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job

URL = "https://jobs.example.com/gone"
USER_KEY = "user-api-key-0123456789"


def _send(
    client: TestClient,
    path: str,
    parts: list[dict],
    metadata: dict | None = None,
    task: dict | None = None,
) -> dict:
    message = {"messageId": f"m-{id(parts)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    response = client.post(
        path,
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": message,
                **({"metadata": metadata} if metadata else {}),
            },
        },
    )
    return response.json()["result"]["task"]


def _searching_container() -> Container:
    """A container whose job-analyst searches once and ranks nothing"""
    container = Container()
    container.job_analyst.agent(
        model=ScriptedChatModel(
            replies=[
                _call("read_file", file_path="/search-jobs/SKILL.md"),
                _call("search_jobs", query="backend engineer"),
                _call("RankedJobs", jobs=[]),
            ]
        )
    )
    return container


def test_find_jobs_asks_ops_api_to_search_and_finishes_on_its_answer():
    client = TestClient(create_app(_searching_container()))

    asked = _send(
        client,
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": analyse_job.INPUT["facts"]}}],
    )
    done = _send(client, "/ezcareer/a2a/find-jobs", [{"data": FOUND}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    [request] = asked["status"]["message"]["parts"]
    assert request["data"] == {
        "execute_tool": "job_search",
        "query": "backend engineer",
        "location": None,
        "country": None,
        "remote_only": False,
        "posted_within": "week",
        "employment_types": [],
        "job_requirements": [],
        "radius_km": None,
        "max_jobs": 10,
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"


def test_a_search_ops_api_cannot_run_fails_the_task_with_its_reason():
    reason = "Connect a job search key in Settings to search for jobs"
    client = TestClient(create_app(_searching_container()))

    asked = _send(
        client,
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": analyse_job.INPUT["facts"]}}],
    )
    failed = _send(
        client, "/ezcareer/a2a/find-jobs", [{"data": {"error": reason}}], task=asked
    )

    assert failed["status"]["state"] == "TASK_STATE_FAILED"
    assert failed["status"]["message"]["parts"] == [{"text": reason}]


def test_parallel_searches_answered_one_at_a_time_each_reach_the_agent():
    model = ScriptedChatModel(
        replies=[
            _call("read_file", file_path="/search-jobs/SKILL.md"),
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "search_jobs", "args": {"query": "backend"}, "id": "c1"},
                    {"name": "search_jobs", "args": {"query": "platform"}, "id": "c2"},
                ],
            ),
            _call("RankedJobs", jobs=[]),
        ]
    )
    container = Container()
    container.job_analyst.agent(model=model)
    client = TestClient(create_app(container))

    asked = _send(
        client,
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": analyse_job.INPUT["facts"]}}],
    )
    left = _send(client, "/ezcareer/a2a/find-jobs", [{"data": FOUND}], task=asked)
    done = _send(
        client,
        "/ezcareer/a2a/find-jobs",
        [{"data": {**FOUND, "requests_left": 1}}],
        task=left,
    )

    assert sorted(p["data"]["query"] for p in asked["status"]["message"]["parts"]) == [
        "backend",
        "platform",
    ]
    assert len(left["status"]["message"]["parts"]) == 1
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    searched = [m for m in model.requests[-1] if isinstance(m, ToolMessage)][-2:]
    assert sorted(json.loads(m.text)["requests_left"] for m in searched) == [
        1,
        FOUND["requests_left"],
    ]


def test_metadata_with_a_key_is_refused_without_echoing_it():
    task = _send(
        TestClient(create_app()),
        "/ezcareer/a2a/find-jobs",
        [{"data": {"facts": analyse_job.INPUT["facts"]}}],
        metadata={"job_search": {"api_key": USER_KEY}},
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert USER_KEY not in json.dumps(task)


def test_job_analyst_flows_have_agent_cards():
    client = TestClient(create_app())

    for name in ("analyse-job", "find-jobs"):
        card = client.get(f"/ezcareer/a2a/{name}/.well-known/agent-card.json")
        assert card.json()["name"] == name


@respx.mock
def test_a_posting_that_cannot_be_fetched_fails_the_task_with_the_reason():
    respx.get(URL).respond(404)
    client = TestClient(create_app())

    task = _send(
        client,
        "/ezcareer/a2a/analyse-job",
        [{"data": {"url": URL, "facts": analyse_job.INPUT["facts"]}}],
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
    container.job_analyst.agent(model=model)

    task = _send(
        TestClient(create_app(container)),
        "/ezcareer/a2a/analyse-job",
        [{"text": "Focus on visa"}, {"data": analyse_job.INPUT}],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["data"]["analysis"]["fit"] == 67
    assert model.requests[0][1].text == "Focus on visa"
    assert "<posting untrusted>" in model.requests[0][2].text


def test_job_analyst_is_served_as_an_agent_with_the_containers_checkpointer():
    container = Container()
    container.job_analyst.agent(model=ScriptedChatModel(replies=[]))

    card = TestClient(create_app(container)).get(
        "/ezcareer/a2a/job-analyst/.well-known/agent-card.json"
    )
    [served] = [e.graph for e in container.executables() if e.name == "job-analyst"]

    assert card.json()["name"] == "job-analyst"
    assert served.checkpointer is container.checkpointer()
    assert container.job_analyst.agent().checkpointer is None


@respx.mock
async def test_both_workflows_run_on_the_containers_one_job_analyst():
    respx.get(analyse_job.URL).respond(200, html=analyse_job.POSTING)
    model = ScriptedChatModel(
        replies=[
            analyse_job._answer("5+ years of Python in production"),
            _call("RankedJobs", jobs=[]),
        ]
    )
    container = Container()
    container.job_analyst.agent(model=model)
    graphs = {e.name: e.graph for e in container.executables()}

    analysed = await graphs["analyse-job"].ainvoke(
        analyse_job.INPUT, {"configurable": {"thread_id": "analyse"}}
    )
    found = await graphs["find-jobs"].ainvoke(
        {"facts": analyse_job.INPUT["facts"]}, {"configurable": {"thread_id": "find"}}
    )

    assert analysed["analysis"].fit == 67
    assert found["jobs"] == []
    assert "<posting untrusted>" in model.requests[0][1].text
    assert "Find jobs for me" in model.requests[1][1].text


def test_a_run_without_profile_facts_fails_with_a_way_to_portfolio():
    task = _send(
        TestClient(create_app()), "/ezcareer/a2a/find-jobs", [{"data": {"facts": []}}]
    )

    assert task["status"]["state"] == "TASK_STATE_FAILED"
    assert task["status"]["message"]["parts"] == [
        {
            "text": "No profile facts were provided. Provide the user's profile facts to run this."
        },
        {"data": {"next": {"label": "Add your experience", "screen": "portfolio"}}},
    ]
