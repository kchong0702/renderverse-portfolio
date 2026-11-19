from datetime import UTC, datetime

from src.features.calendar import service as calendar_service
from tests.conftest import (
    PREFIX,
    a2a_sent,
    connect_google,
    interrupt_part,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
)

CHAT = f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f"


async def _answer(client, harness, request: dict) -> dict:
    """What ops-api resumed the assistant with after it paused on this tool"""
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [interrupt_part(request)])],
        [
            stream_chunk("a-1", "career-director", {"text": "Found them."}),
            stream_status("COMPLETED"),
        ],
    ]
    response = await client.post(
        f"{CHAT}/messages", json={"text": "What's on my calendar?"}
    )
    assert sse_events(response)[-1] == {"status": "completed", "reply": "Found them."}
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]


async def test_events_are_those_from_the_start_of_today_for_the_days_asked(
    client, google, harness, monkeypatch
):
    monkeypatch.setattr(
        calendar_service, "utcnow", lambda: datetime(2026, 11, 13, 4, tzinfo=UTC)
    )
    await connect_google(client)
    google.events = [
        {
            "id": "yesterday",
            "start": {"dateTime": "2026-11-12T20:00:00+08:00"},
            "end": {"dateTime": "2026-11-12T21:00:00+08:00"},
        },
        {
            "id": "this-morning",
            "summary": "Harbor Health interview",
            "start": {"dateTime": "2026-11-13T10:00:00+08:00"},
            "end": {"dateTime": "2026-11-13T11:00:00+08:00"},
        },
        {
            "id": "tomorrow",
            "start": {"date": "2026-11-14"},
            "end": {"date": "2026-11-15"},
        },
        {
            "id": "cancelled",
            "status": "cancelled",
            "start": {"date": "2026-11-14"},
            "end": {"date": "2026-11-15"},
        },
        {
            "id": "after",
            "start": {"dateTime": "2026-11-15T09:00:00+08:00"},
            "end": {"dateTime": "2026-11-15T10:00:00+08:00"},
        },
    ]

    answer = await _answer(client, harness, {"execute_tool": "events", "days": 2})

    assert [event["id"] for event in answer["events"]] == ["this-morning", "tomorrow"]
    assert answer["events"][0]["title"] == "Harbor Health interview"
    assert (answer["timezone"], answer["today"]) == ("Asia/Kuala_Lumpur", "2026-11-13")


async def test_events_say_how_to_connect_google_when_it_isnt(client, harness):
    answer = await _answer(client, harness, {"execute_tool": "events", "days": 7})

    assert answer == {"error": "Connect a Google account in Settings first"}
