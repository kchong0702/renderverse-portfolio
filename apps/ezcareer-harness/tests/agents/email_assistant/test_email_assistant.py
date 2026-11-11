import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from src.app.container import Container
from src.core.errors import ExecuteError
from src.shared.profile import ProfileFact
from tests.agents.career_director.test_handoffs import ACME
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.draft_reply import test_draft_reply_graph as draft_test
from tests.features.triage_email import test_triage_email_graph as triage_test


def _assistant(model: ScriptedChatModel) -> CompiledStateGraph:
    return (
        Container()
        .email_assistant.agent(model=model)
        .copy(update={"checkpointer": InMemorySaver()})
    )


async def _run(
    model: ScriptedChatModel, text: str, *answers: object
) -> tuple[list[object], dict]:
    """Runs email-assistant on text, answering each pause in turn; returns what
    each pause asked and the final state"""
    graph = _assistant(model)
    thread = {"configurable": {"thread_id": "t1"}}
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(text)],
            "facts": [ProfileFact.model_validate(fact) for fact in draft_test.FACTS],
        },
        thread,
    )
    asked: list[object] = []
    for answer in answers:
        asked += [i.value for i in result["__interrupt__"]]
        result = await graph.ainvoke(Command(resume=answer), thread)
    return asked, result


def _report(result: dict, tool: str) -> ToolMessage:
    [report] = [
        m for m in result["messages"] if isinstance(m, ToolMessage) and m.name == tool
    ]
    return report


def _threads(text: str) -> list[dict]:
    return json.loads(
        text.removeprefix("<threads untrusted>\n").removesuffix("\n</threads>")
    )


def _thread(number: int) -> dict:
    return ACME | {"id": f"t-{number}", "subject": f"Update {number}"}


async def test_a_search_under_the_limit_lists_every_matching_thread():
    model = ScriptedChatModel(
        replies=[
            _call("search_threads", keyword="interview", has_attachment=True),
            AIMessage("One thread matches."),
        ]
    )

    asked, result = await _run(
        model, "Find interview emails with attachments", {"threads": [ACME], "total": 1}
    )

    assert asked == [
        {
            "fetch": "threads",
            "since": None,
            "until": None,
            "keyword": "interview",
            "sender": None,
            "has_attachment": True,
            "limit": 20,
        }
    ]
    report = _report(result, "search_threads")
    assert _threads(report.text) == [ACME]
    assert report.artifact == {"step_detail": "1 thread"}


async def test_a_search_over_the_limit_says_how_many_are_hidden_and_to_narrow_it():
    model = ScriptedChatModel(
        replies=[_call("search_threads"), AIMessage("40 threads match.")]
    )

    _, result = await _run(
        model,
        "Show my email",
        {"threads": [_thread(n) for n in range(25)], "total": 40},
    )

    report = _report(result, "search_threads")
    shown, note = report.text.split("\n\n")
    assert [t["id"] for t in _threads(shown)] == [f"t-{n}" for n in range(20)]
    assert note.startswith("Matching threads not shown: 20.")
    assert "narrow the search" in note
    assert report.artifact == {"step_detail": "20 of 40 threads"}
    assert "not shown: 20" in model.requests[-1][-1].text


async def test_a_search_ops_api_cannot_run_tells_the_agent_why():
    model = ScriptedChatModel(
        replies=[_call("search_threads"), AIMessage("Your inbox isn't connected.")]
    )

    _, result = await _run(model, "Show my email", {"error": "Gmail not connected"})

    report = _report(result, "search_threads")
    assert report.status == "error" and "Gmail not connected" in report.text


async def test_a_threads_answer_that_does_not_parse_fails_the_run():
    model = ScriptedChatModel(replies=[_call("search_threads")])

    with pytest.raises(ExecuteError, match="The threads didn't load"):
        await _run(model, "Show my email", {"threads": "not a list"})


async def test_draft_reply_fetches_the_thread_and_free_slots_then_drafts():
    model = ScriptedChatModel(
        replies=[
            _call("draft_reply", thread_id="t-1", request="Say Wednesday works"),
            draft_test._draft(1),
            AIMessage("Here is a draft offering Wednesday."),
        ]
    )

    asked, result = await _run(
        model,
        "Reply that Wednesday works",
        {"thread": triage_test.THREAD},
        {"free_slots": draft_test.FREE_SLOTS, "timezone": "Europe/London"},
    )

    assert asked == [
        {"fetch": "thread", "id": "t-1"},
        {"fetch": "free_slots", "days": 7},
    ]
    assert json.loads(_report(result, "draft_reply").text) == {
        "body": draft_test.BODY,
        "slots": [draft_test.FREE_SLOTS[0]],
    }
    assert model.requests[1][1].text == "Say Wednesday works"
    assert "<thread untrusted>" in model.requests[1][2].text


async def test_a_thread_that_does_not_load_tells_the_agent_why():
    model = ScriptedChatModel(
        replies=[_call("draft_reply", thread_id="t-9"), AIMessage("It's gone.")]
    )

    asked, result = await _run(model, "Reply to t-9", {"error": "No thread t-9"})

    assert asked == [{"fetch": "thread", "id": "t-9"}]
    report = _report(result, "draft_reply")
    assert report.status == "error" and "No thread t-9" in report.text
