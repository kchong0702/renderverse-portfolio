from base64 import urlsafe_b64encode
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import httpx2
import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import create_async_engine

from src.adapters.storage import LocalStorage
from src.core.auth.models import User
from src.core.config import get_settings
from src.db.session import create_session_factory
from src.features.calendar import service as calendar_service
from tests.conftest import (
    PREFIX,
    FakeArtifact,
    FakeGoogle,
    FakeHarness,
    FakeJSearch,
    _app,
    _client,
    a2a_sent,
    a2a_task,
    connect_google,
    idle_in_transaction,
    sse_events,
    stream_chunk,
    stream_status,
    stream_task,
)
from tests.core.conftest import DATABASE_URL

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

    assert response.status_code == 422
    assert response.json() == {"reason": "No facts to draft from", "next": portfolio}


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


async def _executed(client, harness, request: dict) -> dict:
    """What ops-api resumed career-director's draft_reply with after it paused on this tool"""
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": request}])],
        [
            stream_chunk("a-1", "career-director", {"text": "Drafted."}),
            stream_status("COMPLETED"),
        ],
    ]
    response = await client.post(
        f"{PREFIX}/assistant/chats/9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f/messages",
        json={"text": "Draft a reply to t-1"},
    )
    assert sse_events(response)[-1] == {"status": "completed", "reply": "Drafted."}
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]


async def test_career_director_reads_the_thread_it_drafts_a_reply_to(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": THREAD}

    answer = await _executed(client, harness, {"execute_tool": "thread", "id": "t-1"})

    assert answer == {
        "thread": {
            "subject": "Final round",
            "messages": [
                {
                    "sender": "Aisha Rahman <aisha@lumenpay.com>",
                    "sent_at": "2025-11-09T01:12:00Z",
                    "text": "Could you share times?",
                }
            ],
        }
    }


async def test_a_thread_ops_cannot_read_is_answered_with_why(client, google, harness):
    unconnected = await _executed(
        client, harness, {"execute_tool": "thread", "id": "t-1"}
    )
    await connect_google(client)
    missing = await _executed(client, harness, {"execute_tool": "thread", "id": "t-9"})
    unsafe = await _executed(
        client, harness, {"execute_tool": "thread", "id": "../profile"}
    )

    assert unconnected == {"error": "Connect a Google account in Settings first"}
    assert missing == {"error": "Google has no such item"}
    assert list(unsafe) == ["error"]


async def test_career_director_reads_free_slots_for_the_days_it_asks(
    client, google, harness
):
    await connect_google(client)
    google.events = EVENTS

    answer = await _executed(client, harness, {"execute_tool": "free_slots", "days": 3})

    assert answer == {"free_slots": FREE[:3], "timezone": "Asia/Kuala_Lumpur"}
    [params] = google.calendar_params
    assert params["timeMax"] == ["2026-11-14T12:00:00+00:00"]


async def test_career_director_gets_no_free_slots_with_the_rule_off(
    client, google, harness
):
    await connect_google(client)
    await client.patch(
        f"{PREFIX}/settings", json={"automation": {"offer_free_slots": False}}
    )
    google.events = EVENTS

    answer = await _executed(client, harness, {"execute_tool": "free_slots", "days": 3})

    assert answer == {"free_slots": [], "timezone": "Asia/Kuala_Lumpur"}


def _email(thread_id: str, sender: str, subject: str, sent_ms: int, **payload):
    """A Gmail message in thread_id, its payload extended with payload"""
    return {
        "id": f"m-{sent_ms}",
        "threadId": thread_id,
        "snippet": "",
        "internalDate": str(sent_ms),
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": subject},
            ],
            **payload,
        },
    }


RIVERSTONE = "Daniel Lim <daniel@riverstone.com>"

MAILBOX = [
    _email(
        "t-late",
        "Orbit Media HR <hr@orbit.media>",
        "Your offer letter",
        1794357000000,
    ),
    _email(
        "t-rs",
        RIVERSTONE,
        "Re: Next steps for the data platform role",
        1794300000000,
        parts=[{"mimeType": "application/pdf", "filename": "brief.pdf"}],
    ),
    _email("t-old", RIVERSTONE, "Data platform role", 1793869200000),
    _email("t-rs", "Kelvin <kelvin@gmail.com>", "Next steps", 1793696400000),
    _email("t-oct", RIVERSTONE, "Data platform role", 1790845200000),
]


async def test_career_director_searches_threads_with_the_filters_it_sets(
    client, google, harness
):
    await connect_google(client)
    google.messages = {m["id"]: m for m in MAILBOX}

    answer = await _executed(
        client,
        harness,
        {
            "execute_tool": "threads",
            "since": "2026-11-01",
            "until": "2026-11-10",
            "keyword": "data platform",
            "sender": "riverstone.com",
            "has_attachment": True,
            "limit": 20,
        },
    )

    [search] = google.thread_searches
    assert search["q"] == [
        (
            'after:2026/11/01 before:2026/11/11 from:"riverstone.com" has:attachment'
            ' "data" "platform"'
        )
    ]
    assert answer == {
        "threads": [
            {
                "id": "t-rs",
                "subject": "Next steps",
                "sender": RIVERSTONE,
                "last_sent_at": "2026-11-10T08:40:00Z",
                "message_count": 2,
                "has_attachment": True,
            }
        ],
        "total": 1,
    }


async def test_a_thread_search_sends_at_most_its_limit_and_how_many_match(
    client, google, harness
):
    await connect_google(client)
    google.messages = {m["id"]: m for m in MAILBOX}

    answer = await _executed(
        client,
        harness,
        {
            "execute_tool": "threads",
            "sender": "riverstone",
            "has_attachment": False,
            "limit": 1,
        },
    )
    every = await _executed(client, harness, {"execute_tool": "threads", "limit": 500})

    assert google.thread_searches[0]["q"] == ['from:"riverstone" -has:attachment']
    assert [t["id"] for t in answer["threads"]] == ["t-old"]
    assert answer["total"] == 2
    assert google.thread_searches[1]["q"] == [""]
    assert google.thread_searches[1]["maxResults"] == ["25"]
    assert [t["id"] for t in every["threads"]] == ["t-late", "t-rs", "t-old", "t-oct"]


async def test_a_thread_search_with_an_unsafe_value_never_reaches_gmail(
    client, google, harness
):
    await connect_google(client)

    sender = await _executed(
        client,
        harness,
        {"execute_tool": "threads", "sender": 'x" OR from:"boss', "limit": 20},
    )
    keyword = await _executed(
        client,
        harness,
        {"execute_tool": "threads", "keyword": 'offer" OR "x', "limit": 20},
    )
    day = await _executed(
        client, harness, {"execute_tool": "threads", "since": "last week", "limit": 20}
    )

    assert [list(sender), list(keyword), list(day)] == [["error"]] * 3
    assert google.thread_searches == []


class _ProbedGoogle(FakeGoogle):
    def __init__(self):
        """Count, on each call, the connections left idle in a transaction"""
        super().__init__()
        self.idle_in_transaction: list[int] = []

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Answer as FakeGoogle once the connections idle in a transaction are
        counted"""
        self.idle_in_transaction.append(await idle_in_transaction())
        return super().__call__(request)


@pytest.fixture
def probed_google() -> _ProbedGoogle:
    return _ProbedGoogle()


@pytest.fixture
async def probed_client(
    harness: FakeHarness,
    artifact: FakeArtifact,
    probed_google: _ProbedGoogle,
    jsearch: FakeJSearch,
    storage: LocalStorage,
) -> AsyncIterator[httpx2.AsyncClient]:
    """The app on the test Postgres database with probed_google, its dev user
    deleted after the test"""
    engine = create_async_engine(DATABASE_URL)
    async for app in _app(
        harness, artifact, probed_google, jsearch, storage, engine=engine
    ):
        async with _client(app) as http:
            yield http
        async with create_session_factory(engine)() as session, session.begin():
            await session.execute(
                delete(User).where(User.email == get_settings().auth.dev_email)
            )


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_the_gmail_and_calendar_tools_hold_no_transaction_while_google_answers(
    probed_client, probed_google, harness
):
    await connect_google(probed_client)
    probed_google.messages = {"m1": THREAD}
    probed_google.events = EVENTS
    probed_google.idle_in_transaction.clear()

    thread = await _executed(
        probed_client, harness, {"execute_tool": "thread", "id": "t-1"}
    )
    threads = await _executed(
        probed_client, harness, {"execute_tool": "threads", "limit": 5}
    )
    free = await _executed(
        probed_client, harness, {"execute_tool": "free_slots", "days": 3}
    )

    assert thread["thread"]["subject"] == "Final round"
    assert [t["id"] for t in threads["threads"]] == ["t-1"]
    assert free["free_slots"] == FREE[:3]
    assert set(probed_google.idle_in_transaction) == {0}
