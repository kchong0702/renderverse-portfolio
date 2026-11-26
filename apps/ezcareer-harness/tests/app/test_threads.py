from typing import Any, override

import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import JsonValue
from pydantic_core import to_jsonable_python

from src.app.app import create_app
from src.app.container import Container
from src.infrastructure.persistence import MemoryTaskOwners
from tests.agents.career_consultant.test_career_consultant import _state
from tests.agents.test_builder import _call
from tests.app import ops_api
from tests.conftest import ScriptedChatModel

SUMMARY = "Ada wants a backend job."
FIRST = "alpha " * 28_000
SECOND = "bravo " * 28_000
"""Each about 42% of the model's input limit, so the second turn passes 85%"""

FACTS = to_jsonable_python(_state()["profile_facts"])
CONSULTANT = {"document_id": "doc-1", "profile_facts": FACTS}
TURNS = [
    ("career-consultant", "career-consultant", CONSULTANT),
    ("career-director", "career-director", {"profile_facts": FACTS, "preferences": {}}),
]


class SummarisingChatModel(ScriptedChatModel):
    summaries: int = 0
    """How many summaries deepagents asked it for"""

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Any = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        """Answers deepagents' summary prompt with SUMMARY, and anything else in turn"""
        if "Context Extraction Assistant" in messages[0].text[:100]:
            self.summaries += 1
            return ChatResult(generations=[ChatGeneration(message=AIMessage(SUMMARY))])
        return super()._generate(messages, stop, run_manager, **kwargs)


def _client(agent: str) -> tuple[TestClient, SummarisingChatModel]:
    """A client of a fresh app whose agent answers each turn on a model that
    summarises once a conversation passes 85% of 100,000 tokens"""
    model = SummarisingChatModel(
        replies=[AIMessage(f"Reply {n}.") for n in range(1, 6)],
        profile={"max_input_tokens": 100_000},
    )
    container = Container()
    getattr(container, agent.replace("-", "_")).agent(model=model)
    return TestClient(create_app(container)), model


def _say(
    client: TestClient, path: str, text: str, data: dict[str, JsonValue]
) -> dict[str, JsonValue]:
    """One turn of thread-1"""
    return ops_api.send(
        client,
        f"/ezcareer/a2a/{path}",
        [{"text": text}, {"data": data}],
        context="thread-1",
    )


def _summary_url(path: str) -> str:
    """The summary API's URL for thread-1 of the agent served at path"""
    return f"/ezcareer/threads/thread-1/summary?agent={path}"


@pytest.mark.parametrize(("path", "agent", "data"), TURNS)
def test_a_summary_made_on_one_turn_stands_in_on_the_next(
    path: str, agent: str, data: dict[str, JsonValue]
):
    client, model = _client(agent)

    for text in (FIRST, SECOND, "What next?"):
        assert _say(client, path, text, data)["status"]["state"] == (
            "TASK_STATE_COMPLETED"
        )

    assert model.summaries == 1
    [summarised, *_] = model.requests[-1][1:]
    assert f"<summary>\n{SUMMARY}\n</summary>" in summarised.text
    assert all(FIRST not in m.text for m in model.requests[-1])
    assert client.get(_summary_url(path)).json() == {"summary": SUMMARY}


@pytest.mark.parametrize(("path", "agent", "data"), TURNS)
def test_an_edited_summary_is_what_the_agent_sees_next(
    path: str, agent: str, data: dict[str, JsonValue]
):
    client, model = _client(agent)
    for text in (FIRST, SECOND):
        _say(client, path, text, data)

    edited = client.put(_summary_url(path), json={"summary": "Ada wants a staff role."})
    done = _say(client, path, "What next?", data)

    assert edited.json() == {"summary": "Ada wants a staff role."}
    assert done["status"]["state"] == "TASK_STATE_COMPLETED"
    assert model.summaries == 1
    [summarised, *_] = model.requests[-1][1:]
    assert "<summary>\nAda wants a staff role.\n</summary>" in summarised.text
    assert client.get(_summary_url(path)).json() == {
        "summary": "Ada wants a staff role."
    }


def test_a_thread_without_a_summary_reads_as_none_and_cannot_be_edited():
    client, _ = _client("career-consultant")
    _say(client, "career-consultant", "Hi", CONSULTANT)

    read = client.get(_summary_url("career-consultant"))
    edit = client.put(_summary_url("career-consultant"), json={"summary": SUMMARY})
    unknown = client.get("/ezcareer/threads/thread-1/summary?agent=job-analyst")

    assert read.json() == {"summary": None}
    assert edit.status_code == 404
    assert unknown.status_code == 422


def test_a_summary_cannot_be_edited_while_a_run_holds_the_thread_or_it_waits_for_an_answer():
    model = ScriptedChatModel(
        replies=[_call("clarify", question="Which bullet?"), AIMessage("Done.")]
    )
    held: set[str] = set()
    container = Container()
    container.career_consultant.agent(model=model)
    container.task_owners.override(providers.Object(MemoryTaskOwners(threads=held)))
    client = TestClient(create_app(container))
    paused = _say(client, "career-consultant", "Shorten a bullet", CONSULTANT)

    while_paused = client.put(
        _summary_url("career-consultant"), json={"summary": SUMMARY}
    )
    answered = ops_api.send(
        client, "/ezcareer/a2a/career-consultant", [{"text": "The first"}], task=paused
    )
    held.add("thread-1")
    while_held = client.put(
        _summary_url("career-consultant"), json={"summary": SUMMARY}
    )
    held.discard("thread-1")
    after = client.put(_summary_url("career-consultant"), json={"summary": SUMMARY})

    assert paused["status"]["state"] == "TASK_STATE_INPUT_REQUIRED"
    assert while_paused.status_code == 409
    assert answered["status"]["state"] == "TASK_STATE_COMPLETED"
    assert while_held.status_code == 409
    assert after.status_code == 404
