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
        .productivity_assistant.agent(model=model)
        .copy(update={"checkpointer": InMemorySaver()})
    )


async def _run(
    model: ScriptedChatModel, text: str, *answers: object
) -> tuple[list[object], dict]:
    """Runs productivity-assistant on text, answering each pause in turn; returns what
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
            "execute_tool": "threads",
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


async def test_on_its_own_productivity_assistant_is_never_offered_handoff_to_parent():
    model = ScriptedChatModel(replies=[AIMessage("Hello.")])

    await _run(model, "Hi")

    assert {"search_threads", "read_thread", "read_free_slots"} <= (
        model.offered_tools[0]
    )
    assert "handoff_to_parent" not in model.offered_tools[0]


async def test_read_thread_shows_a_long_threads_latest_messages_cut_to_length():
    message = triage_test.THREAD["messages"][0]
    thread = triage_test.THREAD | {
        "messages": [
            message | {"text": f"Message {number}. " + "x" * 5000}
            for number in range(1, 9)
        ]
    }
    model = ScriptedChatModel(
        replies=[_call("read_thread", thread_id="t-1"), AIMessage("Read it.")]
    )

    asked, result = await _run(model, "Read the Acme thread", {"thread": thread})

    assert asked == [{"execute_tool": "thread", "id": "t-1"}]
    report = _report(result, "read_thread")
    assert report.text.startswith("2 earlier messages are left out.")
    assert "<thread untrusted>" in report.text
    assert "Message 2." not in report.text and "Message 3." in report.text
    assert report.text.count(" [cut]") == 6
    assert report.artifact == {"step_detail": "8 messages"}


async def test_a_thread_that_does_not_load_tells_the_agent_why():
    model = ScriptedChatModel(
        replies=[_call("read_thread", thread_id="t-9"), AIMessage("It's gone.")]
    )

    asked, result = await _run(model, "Read t-9", {"error": "No thread t-9"})

    assert asked == [{"execute_tool": "thread", "id": "t-9"}]
    report = _report(result, "read_thread")
    assert report.status == "error" and "No thread t-9" in report.text


async def test_read_free_slots_lists_only_the_earliest_twelve_in_the_users_zone():
    many = [
        {"start": f"2026-11-{day:02d}T09:00:00Z", "end": f"2026-11-{day:02d}T09:30:00Z"}
        for day in range(30, 9, -1)
    ]
    model = ScriptedChatModel(
        replies=[_call("read_free_slots", days=21), AIMessage("Tuesday works.")]
    )

    asked, result = await _run(
        model,
        "When am I free?",
        {"free_slots": many, "timezone": "Asia/Kuala_Lumpur"},
    )

    assert asked == [{"execute_tool": "free_slots", "days": 21}]
    report = _report(result, "read_free_slots")
    lines = report.text.splitlines()
    assert lines[0] == "The user's free times, in Asia/Kuala_Lumpur:"
    assert lines[1] == "- Tue 10 Nov 17:00 to 17:30"
    assert lines[-1] == "- Sat 21 Nov 17:00 to 17:30"
    assert len(lines) == 13
    assert report.artifact == {"step_detail": "12 free slots"}


async def test_no_free_slots_says_the_user_has_none_to_offer():
    model = ScriptedChatModel(
        replies=[_call("read_free_slots"), AIMessage("You have no free times.")]
    )

    _, result = await _run(
        model, "When am I free?", {"free_slots": [], "timezone": "UTC"}
    )

    report = _report(result, "read_free_slots")
    assert report.text == "The user has no free times to offer."
    assert report.artifact == {"step_detail": "no free slots"}
