from base64 import urlsafe_b64encode
from datetime import UTC, datetime

import pytest

from src.features.calendar import service as calendar_service
from tests.conftest import PREFIX, a2a_sent, a2a_task, connect_google

INBOX = f"{PREFIX}/inbox"

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

THREAD = {
    "id": "m1",
    "threadId": "t-1",
    "labelIds": ["INBOX"],
    "snippet": "Could you share times?",
    "internalDate": "1762650720000",
    "payload": {
        "mimeType": "text/plain",
        "headers": [
            {"name": "From", "value": "Aisha Rahman <aisha@lumenpay.com>"},
            {"name": "Subject", "value": "Final round"},
        ],
        "body": {"data": urlsafe_b64encode(b"Could you share times?").decode()},
    },
}

EVENTS = [
    {
        "id": "busy",
        "start": {"dateTime": "2026-11-11T10:00:00+08:00"},
        "end": {"dateTime": "2026-11-11T11:00:00+08:00"},
    },
    {
        "id": "free",
        "transparency": "transparent",
        "start": {"dateTime": "2026-11-12T09:00:00+08:00"},
        "end": {"dateTime": "2026-11-12T18:00:00+08:00"},
    },
    {
        "id": "cancelled",
        "status": "cancelled",
        "start": {"dateTime": "2026-11-13T09:00:00+08:00"},
        "end": {"dateTime": "2026-11-13T18:00:00+08:00"},
    },
    {"id": "all-day", "start": {"date": "2026-11-16"}, "end": {"date": "2026-11-17"}},
]

FREE = [
    {"start": "2026-11-11T11:30:00+08:00", "end": "2026-11-11T18:00:00+08:00"},
    {"start": "2026-11-12T09:00:00+08:00", "end": "2026-11-12T18:00:00+08:00"},
    {"start": "2026-11-13T09:00:00+08:00", "end": "2026-11-13T18:00:00+08:00"},
    {"start": "2026-11-16T09:00:00+08:00", "end": "2026-11-16T18:00:00+08:00"},
    {"start": "2026-11-17T09:00:00+08:00", "end": "2026-11-17T18:00:00+08:00"},
]


@pytest.fixture(autouse=True)
def _now(monkeypatch: pytest.MonkeyPatch) -> None:
    """Free slots are read from a fixed Tuesday noon UTC"""
    monkeypatch.setattr(calendar_service, "utcnow", lambda: NOW)


def _drafted(body: str, slots: list[dict[str, str]]) -> dict:
    """draft-reply's reply"""
    return a2a_task(
        "COMPLETED", artifact_parts=[{"data": {"body": body, "slots": slots}}]
    )


def _input(harness) -> dict:
    """The data draft-reply was sent"""
    [sent] = a2a_sent(harness)
    return sent["params"]["message"]["parts"][0]["data"]


async def _application(client) -> dict:
    """Track an application at Lumen Pay"""
    response = await client.post(
        f"{PREFIX}/applications",
        json={
            "company": "Lumen Pay",
            "role": "Backend Engineer",
            "stage": "applied",
            "applied_on": "2026-11-02",
        },
    )
    return response.json()


async def test_a_reply_draft_offers_free_slots_from_the_calendar(
    client, google, harness
):
    await connect_google(client)
    facts = (await client.get(f"{PREFIX}/profile/agent")).json()["facts"]
    google.messages = {"m1": THREAD}
    google.events = EVENTS
    outside = {"start": "2026-11-14T09:00:00+08:00", "end": "2026-11-14T10:00:00+08:00"}
    harness.outcomes = [_drafted("Hi Aisha, any of these work.", [FREE[0], outside])]

    response = await client.post(f"{INBOX}/t-1/reply-draft")

    assert response.status_code == 200
    assert response.json() == {
        "body": "Hi Aisha, any of these work.",
        "slots": [FREE[0]],
    }
    assert harness.received[0].url.path == "/ezcareer/a2a/draft-reply"
    assert _input(harness) == {
        "thread": {
            "subject": "Final round",
            "messages": [
                {
                    "sender": "Aisha Rahman <aisha@lumenpay.com>",
                    "sent_at": "2025-11-09T01:12:00Z",
                    "text": "Could you share times?",
                }
            ],
        },
        "application": None,
        "free_slots": FREE,
        "timezone": "Asia/Kuala_Lumpur",
        "facts": facts,
    }
    [params] = google.calendar_params
    assert params["timeMin"] == ["2026-11-10T12:00:00+00:00"]
    assert params["timeMax"] == ["2026-11-18T12:00:00+00:00"]
    assert google.sent == []


async def test_free_slots_keep_the_scheduling_settings(client, google, harness):
    await connect_google(client)
    await client.patch(
        f"{PREFIX}/settings",
        json={
            "scheduling": {
                "work_day_start": "10:00",
                "work_day_end": "12:30",
                "meeting_gap_minutes": 0,
            }
        },
    )
    google.messages = {"m1": THREAD}
    google.events = EVENTS
    harness.outcomes = [_drafted("Hi", [])]

    await client.post(f"{INBOX}/t-1/reply-draft")

    assert _input(harness)["free_slots"][:2] == [
        {"start": "2026-11-11T11:00:00+08:00", "end": "2026-11-11T12:30:00+08:00"},
        {"start": "2026-11-12T10:00:00+08:00", "end": "2026-11-12T12:30:00+08:00"},
    ]


async def test_a_reply_draft_offers_no_slots_with_the_rule_off(client, google, harness):
    await connect_google(client)
    await client.patch(
        f"{PREFIX}/settings", json={"automation": {"offer_free_slots": False}}
    )
    google.messages = {"m1": THREAD}
    google.events = EVENTS
    harness.outcomes = [_drafted("Hi Aisha, which times suit you?", [FREE[0]])]

    response = await client.post(f"{INBOX}/t-1/reply-draft")

    assert _input(harness)["free_slots"] == []
    assert _input(harness)["timezone"] == "Asia/Kuala_Lumpur"
    assert response.json()["slots"] == []


async def test_a_reply_draft_carries_the_triaged_application(client, google, harness):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": THREAD}
    triaged = {
        "state": "needs_reply",
        "application_id": application["id"],
        "decide_by": None,
        "interview": None,
    }
    harness.outcomes = [
        a2a_task("COMPLETED", artifact_parts=[{"data": triaged}]),
        _drafted("Hi", []),
    ]
    await client.get(INBOX)

    await client.post(f"{INBOX}/t-1/reply-draft")

    assert a2a_sent(harness)[1]["params"]["message"]["parts"][0]["data"][
        "application"
    ] == {
        "company": "Lumen Pay",
        "role": "Backend Engineer",
        "stage": "applied",
        "applied_at": "2026-11-02",
    }


async def test_a_refused_draft_returns_the_screen_to_fix_it(client, google, harness):
    await connect_google(client)
    google.messages = {"m1": THREAD}
    portfolio = {"label": "Add your experience in Portfolio", "screen": "portfolio"}
    harness.outcomes = [
        a2a_task(
            "FAILED",
            status_parts=[
                {"text": "No facts to draft from"},
                {"data": {"next": portfolio}},
            ],
        )
    ]

    response = await client.post(f"{INBOX}/t-1/reply-draft")

    assert response.json() == {
        "status": "failed",
        "reason": "No facts to draft from",
        "next": portfolio,
    }


async def test_a_follow_up_draft_is_written_for_the_application(
    client, google, harness
):
    await connect_google(client)
    application = await _application(client)
    google.events = EVENTS
    harness.outcomes = [_drafted("Hi, any news on my application?", [])]

    response = await client.post(
        f"{PREFIX}/applications/{application['id']}/follow-up-draft"
    )

    assert response.status_code == 200
    assert response.json() == {"body": "Hi, any news on my application?"}
    sent = _input(harness)
    assert sent["thread"] is None
    assert sent["application"] == {
        "company": "Lumen Pay",
        "role": "Backend Engineer",
        "stage": "applied",
        "applied_at": "2026-11-02",
    }
    assert sent["free_slots"] == []
    assert google.sent == []


async def test_a_follow_up_for_an_unknown_application_is_not_found(
    client, google, harness
):
    await connect_google(client)

    response = await client.post(
        f"{PREFIX}/applications/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f/follow-up-draft"
    )

    assert response.status_code == 404
    assert harness.received == []
