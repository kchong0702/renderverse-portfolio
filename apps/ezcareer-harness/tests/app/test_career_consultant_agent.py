from fastapi.testclient import TestClient

from src.app.app import create_app
from src.app.container import Container
from tests.agents.career_consultant.test_career_consultant import _model


def test_career_consultant_is_served_as_an_agent_with_the_containers_checkpointer():
    container = Container()
    container.career_consultant(model=_model())

    card = TestClient(create_app(container)).get(
        "/ezcareer/a2a/career-consultant/.well-known/agent-card.json"
    )
    [served] = [
        e.graph for e in container.executables() if e.name == "career-consultant"
    ]

    assert card.json()["name"] == "career-consultant"
    assert served.checkpointer is container.checkpointer()
    assert container.career_consultant().checkpointer is None
