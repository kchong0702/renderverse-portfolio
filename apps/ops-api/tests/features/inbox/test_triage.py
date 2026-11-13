import asyncio
from base64 import urlsafe_b64encode
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import ANY
from uuid import UUID, uuid4

import httpx2
import pytest
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from src.adapters.storage import LocalStorage
from src.clients.google.client import MISSING_SCOPE
from src.core.auth.models import User
from src.core.config import get_settings
from src.db.session import create_session_factory
from src.features.applications.models import ApplicationStep
from src.features.inbox.models import EmailThread
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
)
from tests.core.conftest import DATABASE_URL

INBOX = f"{PREFIX}/inbox"


def _message(key: str, thread: str, subject: str, text: str) -> dict[str, object]:
    """A Gmail message of the thread as the API returns it"""
    return {
        "id": key,
        "threadId": thread,
        "labelIds": ["INBOX"],
        "snippet": text,
        "internalDate": "1762650720000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": "Aisha Rahman <aisha@lumenpay.com>"},
                {"name": "Subject", "value": subject},
            ],
            "body": {"data": urlsafe_b64encode(text.encode()).decode()},
        },
    }


def _utc(moment: str) -> datetime:
    """A time the API returned, in UTC"""
    return datetime.fromisoformat(moment).replace(tzinfo=UTC)


def _triaged(state: str, **fields: object) -> dict:
    """triage-email's reply"""
    reply = {
        "state": state,
        "application_id": None,
        "decide_by": None,
        "interview": None,
    }
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply | fields}])


def _by_subject(replies: dict[str, dict]):
    """Answer each triage-email request with the reply for its thread's subject"""
    return lambda sent: replies[
        sent["params"]["message"]["parts"][0]["data"]["thread"]["subject"]
    ]


async def _application(client) -> str:
    """Track an application at Lumen Pay and return its id"""
    response = await client.post(
        f"{PREFIX}/applications",
        json={"company": "Lumen Pay", "role": "Backend Engineer", "stage": "applied"},
    )
    return response.json()["id"]


async def test_sync_triages_each_thread_and_counts_those_needing_a_reply(
    client, google, harness
):
    await connect_google(client)
    application = await _application(client)
    google.messages = {
        "m3": _message("m3", "t-1", "Final round", "Could you share times?"),
        "m2": _message("m2", "t-2", "Your offer", "Please decide by Friday."),
        "m1": _message("m1", "t-1", "Final round", "Thanks for applying."),
    }
    replies = {
        "Final round": _triaged("needs_reply", application_id=application),
        "Your offer": _triaged(
            "offer", application_id=application, decide_by="2026-11-14"
        ),
    }
    harness.outcomes = [_by_subject(replies)] * 2

    response = await client.get(INBOX)

    assert response.status_code == 200
    body = response.json()
    assert body["needs_reply"] == 1
    assert [
        (m["id"], m["state"], m["decide_by"], m["application_id"])
        for m in body["messages"]
    ] == [
        ("m3", "needs_reply", None, application),
        ("m2", "offer", "2026-11-14", application),
        ("m1", "needs_reply", None, application),
    ]
    sent = sorted(a2a_sent(harness), key=lambda s: s["params"]["message"]["contextId"])
    assert {r.url.path for r in harness.received} == {"/ezcareer/a2a/triage-email"}
    inputs = {
        s["params"]["message"]["parts"][0]["data"]["thread"]["subject"]: s["params"][
            "message"
        ]["parts"][0]["data"]
        for s in sent
    }
    assert inputs["Final round"] == {
        "thread": {
            "subject": "Final round",
            "messages": [
                {
                    "sender": "Aisha Rahman <aisha@lumenpay.com>",
                    "sent_at": "2025-11-09T01:12:00Z",
                    "text": "Thanks for applying.",
                },
                {
                    "sender": "Aisha Rahman <aisha@lumenpay.com>",
                    "sent_at": "2025-11-09T01:12:00Z",
                    "text": "Could you share times?",
                },
            ],
        },
        "applications": [
            {"id": application, "company": "Lumen Pay", "role": "Backend Engineer"}
        ],
    }
    detail = await client.get(f"{INBOX}/m2")
    assert detail.json()["state"] == "offer"
    assert detail.json()["decide_by"] == "2026-11-14"
    steps = await client.get(f"{PREFIX}/applications/{application}/steps")
    assert [(s["kind"], s["due_on"]) for s in steps.json()] == [
        ("offer_deadline", "2026-11-14")
    ]


async def test_only_new_or_changed_threads_are_triaged_again(client, google, harness):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Thanks.")}
    harness.outcomes = [_triaged("info")]
    await client.get(INBOX)

    unchanged = await client.get(INBOX)
    google.messages = {
        "m2": _message("m2", "t-1", "Final round", "Could you share times?"),
        **google.messages,
    }
    harness.outcomes = [_triaged("needs_reply")]
    changed = await client.get(INBOX)

    assert unchanged.json()["messages"][0]["state"] == "info"
    assert len(harness.received) == 2
    assert changed.json()["needs_reply"] == 1
    assert {m["state"] for m in changed.json()["messages"]} == {"needs_reply"}


async def test_a_thread_the_harness_could_not_triage_is_tried_on_the_next_sync(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Times?")}
    harness.down = True

    down = await client.get(INBOX)
    harness.down = False
    harness.outcomes = [a2a_task("FAILED", status_parts=[{"text": "No model"}])]
    failed = await client.get(INBOX)
    harness.outcomes = [_triaged("needs_reply")]
    triaged = await client.get(INBOX)

    assert down.status_code == 200
    assert down.json() == failed.json()
    assert down.json()["needs_reply"] == 0
    assert down.json()["messages"][0]["state"] is None
    assert triaged.json()["needs_reply"] == 1


async def test_an_application_that_is_not_the_users_is_not_linked(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Times?")}
    harness.outcomes = [_triaged("needs_reply", application_id=str(uuid4()))]

    response = await client.get(INBOX)

    assert response.json()["messages"][0]["application_id"] is None


INTERVIEW = {
    "start": "2030-11-12T10:00:00+08:00",
    "end": None,
    "format": "video",
    "location": "https://meet.google.com/abc",
}


async def test_an_interview_a_thread_confirms_is_added_to_the_calendar_once(
    client, google, harness
):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ]

    first = await client.get(INBOX)
    await client.get(INBOX)

    assert first.json()["messages"][0]["on_calendar"] is True
    [step] = (await client.get(f"{PREFIX}/applications/{application}/steps")).json()
    assert _utc(step["starts_at"]) == datetime(2030, 11, 12, 2, tzinfo=UTC)
    assert {k: step[k] for k in ("kind", "format", "location")} == {
        "kind": "interview",
        "format": "video",
        "location": "https://meet.google.com/abc",
    }
    assert google.created == [
        {
            "id": ANY,
            "summary": "Lumen Pay Backend Engineer interview",
            "start": {"dateTime": "2030-11-12T02:00:00Z"},
            "end": {"dateTime": "2030-11-12T03:00:00Z"},
            "location": "https://meet.google.com/abc",
            "extendedProperties": {"private": {"ops": "interview"}},
        }
    ]


async def test_interviews_are_not_added_with_the_rule_off(client, google, harness):
    await connect_google(client)
    application = await _application(client)
    await client.patch(
        f"{PREFIX}/settings", json={"automation": {"add_interview_invites": False}}
    )
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ]

    response = await client.get(INBOX)

    assert response.json()["messages"][0]["state"] == "interview"
    assert response.json()["messages"][0]["on_calendar"] is False
    assert google.created == []


async def test_a_past_interview_is_not_added(client, google, harness):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Thanks.")}
    past = INTERVIEW | {"start": "2020-11-12T10:00:00+08:00"}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=past)
    ]

    await client.get(INBOX)

    assert google.created == []


async def test_an_interview_waits_for_a_grant_that_adds_events(client, google, harness):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ]
    google.read_only = True

    refused = await client.get(INBOX)
    google.read_only = False
    added = await client.get(INBOX)

    assert refused.status_code == 409
    assert refused.json() == {"detail": MISSING_SCOPE}
    assert added.status_code == 200
    assert len(harness.received) == 1
    assert [event["summary"] for event in google.created] == [
        "Lumen Pay Backend Engineer interview"
    ]


async def test_a_rescheduled_interview_moves_its_step_and_is_added_once(
    client, google, harness
):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ]
    await client.get(INBOX)
    google.messages = {
        "m2": _message("m2", "t-1", "Final round", "Can we move it?"),
        **google.messages,
    }
    moved = INTERVIEW | {"start": "2030-11-13T15:00:00+08:00"}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=moved)
    ]

    response = await client.get(INBOX)

    steps = (await client.get(f"{PREFIX}/applications/{application}/steps")).json()
    assert [(s["kind"], _utc(s["starts_at"])) for s in steps] == [
        ("interview", datetime(2030, 11, 13, 7, tzinfo=UTC))
    ]
    assert response.json()["messages"][0]["on_calendar"] is True
    assert len(google.created) == 1
    assert google.created[0]["start"] == {"dateTime": "2030-11-13T07:00:00Z"}
    assert google.created[0]["end"] == {"dateTime": "2030-11-13T08:00:00Z"}


async def _resync(client, google, harness, key: str, reply: dict) -> httpx2.Response:
    """Sync again after a new message in thread t-1 that triage reads as reply"""
    google.messages = {
        key: _message(key, "t-1", "Final round", "About your interview."),
        **google.messages,
    }
    harness.outcomes = [reply]
    return await client.get(INBOX)


async def _interviewed(client, google, harness) -> tuple[str, str, dict]:
    """Triage a thread confirming an interview at Lumen Pay; return the
    application, its steps URL and the interview step"""
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ]
    await client.get(INBOX)
    steps = f"{PREFIX}/applications/{application}/steps"
    [step] = (await client.get(steps)).json()
    return application, steps, step


async def test_triage_saves_steps_with_no_title(client, google, harness):
    _, _, step = await _interviewed(client, google, harness)

    assert step["title"] == ""


async def test_a_users_edit_survives_a_later_message_at_the_same_time(
    client, google, harness
):
    application, steps, step = await _interviewed(client, google, harness)
    await client.put(
        f"{steps}/{step['id']}", json={**step, "location": "Level 3, Menara Lumen"}
    )

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=INTERVIEW),
    )

    [kept] = (await client.get(steps)).json()
    assert kept["location"] == "Level 3, Menara Lumen"


async def test_a_second_round_in_the_thread_is_a_new_step_with_its_own_event(
    client, google, harness
):
    application, steps, first = await _interviewed(client, google, harness)
    await client.put(f"{steps}/{first['id']}", json={**first, "status": "done"})
    second_round = INTERVIEW | {"start": "2030-11-19T10:00:00+08:00"}

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=second_round),
    )

    listed = (await client.get(steps)).json()
    assert [(s["status"], _utc(s["starts_at"])) for s in listed] == [
        ("done", datetime(2030, 11, 12, 2, tzinfo=UTC)),
        ("open", datetime(2030, 11, 19, 2, tzinfo=UTC)),
    ]
    [tracked] = (await client.get(f"{PREFIX}/applications")).json()
    assert tracked["next_step"]["id"] == listed[1]["id"]
    assert [e["start"] for e in google.created] == [
        {"dateTime": "2030-11-12T02:00:00Z"},
        {"dateTime": "2030-11-19T02:00:00Z"},
    ]


async def test_a_second_round_after_an_unfinished_first_is_a_new_step_with_its_own_event(
    client, google, harness
):
    await connect_google(client)
    application = await _application(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    first_round = INTERVIEW | {"start": "2020-11-12T10:00:00+08:00"}
    harness.outcomes = [
        _triaged("interview", application_id=application, interview=first_round)
    ]
    await client.get(INBOX)
    second_round = INTERVIEW | {"start": "2030-11-19T10:00:00+08:00"}

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=second_round),
    )

    steps = f"{PREFIX}/applications/{application}/steps"
    assert [
        (s["status"], _utc(s["starts_at"])) for s in (await client.get(steps)).json()
    ] == [
        ("open", datetime(2020, 11, 12, 2, tzinfo=UTC)),
        ("open", datetime(2030, 11, 19, 2, tzinfo=UTC)),
    ]
    assert [e["start"] for e in google.created] == [
        {"dateTime": "2030-11-19T02:00:00Z"}
    ]


async def test_a_users_new_time_survives_a_later_message_at_the_old_time(
    client, google, harness
):
    application, steps, step = await _interviewed(client, google, harness)
    await client.put(
        f"{steps}/{step['id']}", json={**step, "starts_at": "2030-11-12T03:00:00Z"}
    )

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=INTERVIEW),
    )

    [kept] = (await client.get(steps)).json()
    assert _utc(kept["starts_at"]) == datetime(2030, 11, 12, 3, tzinfo=UTC)


async def test_a_users_new_time_moves_the_calendar_event(client, google, harness):
    _, steps, step = await _interviewed(client, google, harness)

    await client.put(
        f"{steps}/{step['id']}", json={**step, "starts_at": "2030-11-12T03:00:00Z"}
    )

    assert (google.created[0]["start"], google.created[0]["end"]) == (
        {"dateTime": "2030-11-12T03:00:00Z"},
        {"dateTime": "2030-11-12T04:00:00Z"},
    )


async def test_cancelling_a_step_deletes_its_calendar_event(client, google, harness):
    _, steps, step = await _interviewed(client, google, harness)

    await client.put(f"{steps}/{step['id']}", json={**step, "status": "cancelled"})

    assert google.created[0]["status"] == "cancelled"
    assert (await client.get(INBOX)).json()["messages"][0]["on_calendar"] is False


async def test_a_deleted_step_found_again_is_not_added_to_the_calendar_twice(
    client, google, harness
):
    application, steps, step = await _interviewed(client, google, harness)
    await client.delete(f"{steps}/{step['id']}")

    response = await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=INTERVIEW),
    )

    assert len((await client.get(steps)).json()) == 1
    assert len(google.created) == 1
    assert response.json()["messages"][0]["on_calendar"] is True


async def test_a_step_about_no_tracked_application_can_be_done_and_deleted(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [_triaged("interview", interview=INTERVIEW)]
    await client.get(INBOX)
    found = f"{PREFIX}/applications/steps"
    week = {"start": "2030-11-12T00:00:00Z", "end": "2030-11-13T00:00:00Z"}
    [step] = (await client.get(found, params=week)).json()

    done = await client.put(f"{found}/{step['id']}", json={**step, "status": "done"})
    deleted = await client.delete(f"{found}/{step['id']}")

    assert done.json()["status"] == "done"
    assert deleted.status_code == 204
    assert (await client.get(found, params=week)).json() == []


async def test_a_cancelled_step_is_not_revived(client, google, harness):
    application, steps, step = await _interviewed(client, google, harness)
    await client.put(f"{steps}/{step['id']}", json={**step, "status": "cancelled"})

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("interview", application_id=application, interview=INTERVIEW),
    )

    assert [s["status"] for s in (await client.get(steps)).json()] == ["cancelled"]
    assert len(google.created) == 1


async def test_a_step_found_in_an_email_keeps_its_kind(client, google, harness):
    _, steps, step = await _interviewed(client, google, harness)

    retyped = await client.put(
        f"{steps}/{step['id']}", json={**step, "kind": "follow_up"}
    )
    moved = await client.put(
        f"{steps}/{step['id']}", json={**step, "location": "Level 3"}
    )

    assert retyped.status_code == 422
    assert moved.status_code == 200


async def test_an_interview_about_no_tracked_application_is_kept_on_its_thread(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [_triaged("interview", interview=INTERVIEW)]

    response = await client.get(INBOX)

    assert response.json()["messages"][0]["on_calendar"] is True
    assert [e["summary"] for e in google.created] == ["Interview"]
    listed = await client.get(
        f"{PREFIX}/applications/steps",
        params={"start": "2030-11-12T00:00:00Z", "end": "2030-11-13T00:00:00Z"},
    )
    assert [(s["kind"], s["application_id"]) for s in listed.json()] == [
        ("interview", None)
    ]


async def test_a_thread_linked_later_puts_its_steps_on_the_application(
    client, google, harness
):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Decide soon.")}
    harness.outcomes = [_triaged("offer", decide_by="2026-11-14")]
    unlinked = await client.get(INBOX)
    application = await _application(client)

    await _resync(
        client,
        google,
        harness,
        "m2",
        _triaged("offer", application_id=application, decide_by="2026-11-14"),
    )

    assert unlinked.json()["messages"][0]["decide_by"] == "2026-11-14"
    steps = (await client.get(f"{PREFIX}/applications/{application}/steps")).json()
    assert [(s["kind"], s["due_on"]) for s in steps] == [
        ("offer_deadline", "2026-11-14")
    ]


class _OverlappingHarness(FakeHarness):
    def __init__(self):
        """Hold each triage until a second one starts, so two syncs overlap"""
        super().__init__()
        self.triaging = asyncio.Barrier(2)

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Answer as FakeHarness once two triages are running"""
        if request.url.path.endswith("/triage-email"):
            await asyncio.wait_for(self.triaging.wait(), 5)
        return super().__call__(request)


class _OverlappingGoogle(FakeGoogle):
    def __init__(self):
        """Hold the first new event until another sync sends one or waits on a row"""
        super().__init__()
        self.inserts = 0

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        """Answer as FakeGoogle once a second sync has caught up with the first"""
        if request.method == "POST" and request.url.path.endswith("/events"):
            self.inserts += 1
            engine = create_async_engine(DATABASE_URL, poolclass=NullPool)
            async with asyncio.timeout(5), engine.connect() as db:
                while self.inserts < 2 and not await db.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity"
                        " WHERE datname = current_database()"
                        " AND wait_event_type = 'Lock'"
                    )
                ):
                    await asyncio.sleep(0.01)
        return super().__call__(request)


@pytest.fixture
def overlapping() -> _OverlappingHarness:
    return _OverlappingHarness()


@pytest.fixture
def overlapping_google() -> _OverlappingGoogle:
    return _OverlappingGoogle()


@pytest.fixture
async def postgres_client(
    overlapping: _OverlappingHarness,
    artifact: FakeArtifact,
    overlapping_google: _OverlappingGoogle,
    jsearch: FakeJSearch,
    storage: LocalStorage,
) -> AsyncIterator[httpx2.AsyncClient]:
    """The app on the test Postgres database, its dev user deleted after the test"""
    engine = create_async_engine(DATABASE_URL)
    async for app in _app(
        overlapping, artifact, overlapping_google, jsearch, storage, engine=engine
    ):
        async with _client(app) as http:
            yield http
        async with create_session_factory(engine)() as session, session.begin():
            await session.execute(
                delete(User).where(User.email == get_settings().auth.dev_email)
            )


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_deleting_a_thread_deletes_the_steps_found_in_it(
    postgres_app, google, harness
):
    async with _client(postgres_app) as client:
        await connect_google(client)
        google.messages = {"m1": _message("m1", "t-1", "Final round", "See you.")}
        harness.outcomes = [_triaged("interview", interview=INTERVIEW)]
        await client.get(INBOX)
        [step] = (
            await client.get(
                f"{PREFIX}/applications/steps",
                params={"start": "2030-11-12T00:00:00Z", "end": "2030-11-13T00:00:00Z"},
            )
        ).json()

    async with postgres_app.state.session_factory() as session, session.begin():
        await session.execute(
            delete(EmailThread).where(EmailThread.id == UUID(step["email_thread_id"]))
        )

    async with postgres_app.state.session_factory() as session:
        assert await session.get(ApplicationStep, UUID(step["id"])) is None


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_overlapping_first_syncs_of_a_thread_both_succeed(
    postgres_client, overlapping, overlapping_google
):
    await connect_google(postgres_client)
    overlapping_google.messages = {"m1": _message("m1", "t-1", "Final round", "Times?")}
    overlapping.outcomes = [_triaged("needs_reply")] * 2

    first, second = await asyncio.gather(
        postgres_client.get(INBOX), postgres_client.get(INBOX)
    )
    after = await postgres_client.get(INBOX)

    assert [first.status_code, second.status_code] == [200, 200]
    assert after.json()["needs_reply"] == 1
    assert len(overlapping.received) == 2


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_overlapping_syncs_add_an_interview_to_the_calendar_once(
    postgres_client, overlapping, overlapping_google
):
    await connect_google(postgres_client)
    await postgres_client.get(f"{PREFIX}/settings")
    application = await _application(postgres_client)
    overlapping_google.messages = {
        "m1": _message("m1", "t-1", "Final round", "See you then.")
    }
    overlapping.outcomes = [
        _triaged("interview", application_id=application, interview=INTERVIEW)
    ] * 2

    first, second = await asyncio.gather(
        postgres_client.get(INBOX), postgres_client.get(INBOX)
    )

    assert [first.status_code, second.status_code] == [200, 200]
    assert overlapping_google.inserts == 1
    assert [e["summary"] for e in overlapping_google.created] == [
        "Lumen Pay Backend Engineer interview"
    ]
