from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from src.app.container import Container
from tests.agents.career_consultant import test_career_consultant as career_consultant
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.draft_reply import test_draft_reply_graph as draft_test
from tests.features.triage_email import test_triage_email_graph as triage_test

ACME = {
    "id": "t-1",
    "subject": "Your interview with Acme Payments",
    "sender": "Priya Shah <priya@acme.com>",
    "last_sent_at": "2026-11-09T09:12:00Z",
    "message_count": 2,
    "has_attachment": False,
}


def _graph(director: ScriptedChatModel, assistant: ScriptedChatModel):
    container = Container()
    container.career_director.agent(model=director)
    container.productivity_assistant.agent(model=assistant)
    return container.career_director.agent_executable().graph


async def _turn(
    graph: CompiledStateGraph, text: str, *answers: object
) -> tuple[list[object], dict]:
    """Sends text as one turn of conversation c1, answering each pause in turn;
    returns what each pause asked and the final state"""
    thread = {"configurable": {"thread_id": "c1"}}
    result = await graph.ainvoke(
        {
            "messages": [HumanMessage(text)],
            "facts": career_consultant._state()["facts"],
            "preferences": {},
        },
        thread,
    )
    asked: list[object] = []
    for answer in answers:
        asked += [i.value for i in result["__interrupt__"]]
        result = await graph.ainvoke(Command(resume=answer), thread)
    return asked, result


async def test_email_goes_to_productivity_assistant_which_keeps_the_next_turn_and_hands_back():
    director = ScriptedChatModel(
        replies=[
            _call("handoff_to_child", agent="productivity-assistant"),
            AIMessage("Here are some jobs."),
        ]
    )
    assistant = ScriptedChatModel(
        replies=[
            _call("search_threads", sender="acme.com", since="2026-11-02"),
            AIMessage("Priya from Acme wrote about your interview."),
            _call("read_thread", thread_id="t-1"),
            _call("read_free_slots"),
            AIMessage(draft_test.BODY),
            _call("handoff_to_parent"),
        ]
    )
    graph = _graph(director, assistant)

    found_asked, found = await _turn(
        graph, "What did Acme email me this week?", {"threads": [ACME], "total": 1}
    )
    drafted_asked, drafted = await _turn(
        graph,
        "Reply to Priya that Wednesday works",
        {"thread": triage_test.THREAD},
        {"free_slots": draft_test.FREE_SLOTS, "timezone": "Europe/London"},
    )
    _, back = await _turn(graph, "Now find me jobs")

    assert found_asked == [
        {
            "execute_tool": "threads",
            "since": "2026-11-02",
            "until": None,
            "keyword": None,
            "sender": "acme.com",
            "has_attachment": None,
            "limit": 20,
        }
    ]
    assert found["active_agent"] == "productivity-assistant"
    assert found["messages"][-1].text == "Priya from Acme wrote about your interview."
    assert drafted_asked == [
        {"execute_tool": "thread", "id": "t-1"},
        {"execute_tool": "free_slots", "days": 7},
    ]
    assert drafted["messages"][-1].text == draft_test.BODY
    assert "<thread untrusted>" in assistant.requests[3][-1].text
    assert "Wed 11 Nov 10:00 to 10:30" in assistant.requests[4][-1].text
    assert back["active_agent"] == "career-director"
    assert back["messages"][-1].text == "Here are some jobs."
    assert len(director.requests) == 2
    assert director.requests[-1][-3].text == "Now find me jobs"


async def test_only_the_child_agents_in_the_graph_are_offered_handoff_to_parent():
    director = ScriptedChatModel(
        replies=[_call("handoff_to_child", agent="productivity-assistant")]
    )
    assistant = ScriptedChatModel(replies=[AIMessage("Nothing new.")])

    await _turn(_graph(director, assistant), "Any new email?")

    assert "handoff_to_child" in director.offered_tools[0]
    assert "handoff_to_parent" not in director.offered_tools[0]
    assert {"search_threads", "read_thread", "read_free_slots"} <= (
        assistant.offered_tools[0]
    )
    assert "handoff_to_parent" in assistant.offered_tools[0]
    assert "draft_reply" not in assistant.offered_tools[0]
