import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, ToolMessage
from pydantic import ValidationError

from src.app.app import create_app
from src.app.container import Container
from src.features.draft_reply import DraftReplyInput, build_graph
from src.shared.email import TimeSlot
from tests.agents.test_builder import _call
from tests.conftest import ScriptedChatModel
from tests.features.triage_email.test_triage_email_graph import THREAD

FREE_SLOTS = [
    {"start": "2026-11-11T10:00:00Z", "end": "2026-11-11T10:30:00Z"},
    {"start": "2026-11-12T14:00:00Z", "end": "2026-11-12T14:30:00Z"},
    {"start": "2026-11-13T09:00:00Z", "end": "2026-11-13T09:30:00Z"},
]
FACTS = [{"id": "name", "text": "My name is Aisha Rahman"}]
BODY = "Hi Priya,\n\nThursday 14:00 or Wednesday 10:00 works for me.\n\nAisha"


def _draft(*slot_ids: int, body: str = BODY) -> AIMessage:
    return _call("DraftReply", body=body, slot_ids=list(slot_ids))


def _graph(model: ScriptedChatModel):
    return build_graph(Container().productivity_assistant.agent(model=model))


async def test_a_reply_offers_only_free_slots_and_lists_them_in_the_users_zone():
    model = ScriptedChatModel(
        replies=[_call("read_profile_facts"), _draft(2, 9), _draft(2, 1, 2)]
    )

    result = await _graph(model).ainvoke(
        {
            "thread": THREAD,
            "free_slots": FREE_SLOTS,
            "timezone": "Asia/Kuala_Lumpur",
            "facts": FACTS,
        }
    )

    assert result == {
        "body": BODY,
        "slots": [
            TimeSlot.model_validate(FREE_SLOTS[1]),
            TimeSlot.model_validate(FREE_SLOTS[0]),
        ],
    }
    brief = model.requests[0][1].text
    assert "<thread untrusted>" in brief
    assert "My free slots, in Asia/Kuala_Lumpur:" in brief
    assert "[1] Wed 11 Nov 18:00 to 18:30" in brief
    assert "read_profile_facts" in model.offered_tools[0]
    assert {"handoff_to_parent", "read_thread", "search_threads"}.isdisjoint(
        model.offered_tools[0]
    )
    [facts] = [m for m in model.requests[1] if isinstance(m, ToolMessage)]
    assert "Aisha Rahman" in facts.text
    assert "unknown_slot" in model.requests[-1][-1].text


async def test_only_the_earliest_twelve_free_slots_reach_the_agent():
    many = [
        {"start": f"2026-11-{day:02d}T09:00:00Z", "end": f"2026-11-{day:02d}T09:30:00Z"}
        for day in range(30, 9, -1)
    ]
    model = ScriptedChatModel(replies=[_draft(12, 13), _draft(12)])

    result = await _graph(model).ainvoke(
        {"thread": THREAD, "free_slots": many, "timezone": "UTC", "facts": FACTS}
    )

    brief = model.requests[0][1].text
    assert "[1] Tue 10 Nov 09:00 to 09:30" in brief
    assert "[12] Sat 21 Nov 09:00 to 09:30" in brief
    assert "[13]" not in brief
    assert "unknown_slot" in model.requests[-1][-1].text
    assert result["slots"] == [TimeSlot.model_validate(many[-12])]


async def test_a_follow_up_for_an_application_without_a_thread_offers_no_times():
    model = ScriptedChatModel(replies=[_draft(body="Hi, any news on my application?")])

    result = await _graph(model).ainvoke(
        {
            "application": {
                "company": "Acme Payments",
                "role": "Backend Engineer",
                "stage": "applied",
                "applied_at": "2026-10-28",
            },
            "timezone": "Europe/London",
        }
    )

    assert result == {"body": "Hi, any news on my application?", "slots": []}
    brief = model.requests[0][1].text
    assert "follow-up email for my application for Backend Engineer at Acme" in brief
    assert "sent on 2026-10-28" in brief
    assert "I have no free slots to offer." in brief


def test_a_request_with_neither_a_thread_nor_an_application_is_refused():
    with pytest.raises(ValidationError, match="thread to answer or an application"):
        DraftReplyInput.model_validate({"timezone": "Europe/London"})


def test_draft_reply_is_served_over_a2a():
    container = Container()
    container.productivity_assistant.agent(model=ScriptedChatModel(replies=[_draft(1)]))

    response = TestClient(create_app(container)).post(
        "/ezcareer/a2a/draft-reply",
        headers={"A2A-Version": "1.0"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "SendMessage",
            "params": {
                "message": {
                    "messageId": "m1",
                    "role": "ROLE_USER",
                    "parts": [
                        {"text": "Say Wednesday suits me best"},
                        {
                            "data": {
                                "thread": THREAD,
                                "application": None,
                                "free_slots": FREE_SLOTS,
                                "timezone": "Europe/London",
                                "facts": FACTS,
                            }
                        },
                    ],
                }
            },
        },
    )
    task = response.json()["result"]["task"]

    assert task["status"]["state"] == "TASK_STATE_COMPLETED"
    [reply] = [a for a in task["artifacts"] if a["name"] == "draft-reply"]
    assert reply["parts"][0]["data"] == {
        "body": BODY,
        "slots": [{"start": "2026-11-11T10:00:00Z", "end": "2026-11-11T10:30:00Z"}],
    }


async def test_only_the_latest_messages_of_a_long_thread_reach_the_agent_cut_to_length():
    message = THREAD["messages"][0]
    thread = THREAD | {
        "messages": [
            message | {"text": f"Message {number}. " + "x" * 5000}
            for number in range(1, 9)
        ]
    }
    model = ScriptedChatModel(replies=[_draft()])

    await _graph(model).ainvoke(
        {"thread": thread, "free_slots": [], "timezone": "UTC", "facts": FACTS}
    )

    brief = model.requests[0][1].text
    assert "2 earlier messages of the thread are left out." in brief
    assert "Message 2." not in brief
    assert "Message 3." in brief and "Message 8." in brief
    assert brief.count(" [cut]") == 6
    assert len(brief) < 6 * 4200
