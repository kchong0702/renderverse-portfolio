from fastapi.testclient import TestClient
from pydantic_core import to_jsonable_python

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant.test_career_consultant import (
    DONE,
    GOOD_EDIT,
    READ_SKILL,
    _model,
    _propose,
    _state,
)


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


def test_a_proposal_to_the_served_agent_comes_back_as_a_changeset_artifact():
    container = Container()
    model = _model(READ_SKILL, _propose(GOOD_EDIT), DONE)
    container.career_consultant.agent(model=model)
    state = _state()

    response = TestClient(create_app(container)).post(
        "/ezcareer/a2a/career-consultant",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m-1",
                    "role": "ROLE_USER",
                    "parts": [
                        {"text": state["messages"][0].text},
                        {
                            "data": to_jsonable_python(
                                {k: v for k, v in state.items() if k != "messages"}
                            )
                        },
                    ],
                }
            },
        },
    )

    task = response.json()["result"]["task"]
    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [changeset] = [a for a in task["artifacts"] if a["name"] == "changeset"]
    [part] = changeset["parts"]
    assert part["data"]["changeset"]["edits"] == [GOOD_EDIT.model_dump(mode="json")]
    assert "propose_changeset" not in model.offered_tools[0]
    assert "propose_changeset" in model.offered_tools[1]
