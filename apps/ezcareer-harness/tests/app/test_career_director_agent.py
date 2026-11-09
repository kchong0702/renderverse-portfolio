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
from tests.agents.career_director.test_career_director import REQUEST, _model, _task
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.analyse_job import test_analyse_job_graph as analyse_job
from tests.features.write_document.test_write_document_graph import _print


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


def test_career_director_is_served_as_an_agent_with_the_containers_checkpointer():
    container = Container()
    container.career_director.agent(model=_model())

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
    director = _model(_task("analyse-job", analyse_job.URL), AIMessage("It fits 67%."))
    container = Container()
    container.job_finder.agent(
        model=ScriptedChatModel(
            replies=[analyse_job._answer("5+ years of Python in production")]
        )
    )
    container.career_director.agent(model=director)

    task = _send(
        TestClient(create_app(container)),
        [
            {"text": f"How well do I fit {analyse_job.URL}?"},
            {"data": analyse_job.INPUT["profile"]},
        ],
    )

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    assert task["artifacts"][0]["parts"][0]["text"] == "It fits 67%."
    [report] = [m for m in director.requests[1] if isinstance(m, ToolMessage)]
    assert '"fit":67' in report.text


def test_a_subagents_question_reaches_the_user_and_their_answer_finishes_the_turn():
    container = Container()
    container.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    container.career_consultant.agent(
        model=career_consultant._model(
            _call("clarify", question="Which bullet?"),
            career_consultant._answer(career_consultant.GOOD_EDIT),
        )
    )
    container.career_director.agent(
        model=_model(_task("edit-document", REQUEST), AIMessage("I proposed one edit."))
    )
    client = TestClient(create_app(container))
    state = to_jsonable_python(career_consultant._state())

    asked = _send(
        client,
        [
            {"text": REQUEST},
            {
                "data": {
                    "facts": state["facts"],
                    "preferences": {},
                    "document": state["document"],
                    "lines": state["lines"],
                }
            },
        ],
    )
    done = _send(client, [{"data": {"input": "The queue one"}}], task=asked)

    assert asked["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert asked["status"]["message"]["parts"][0]["data"] == {
        "label": "Which bullet?",
        "input_placeholder": "Type your answer here...",
        "submit_btn": "Send",
    }
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert done["artifacts"][0]["parts"][0]["text"] == "I proposed one edit."
