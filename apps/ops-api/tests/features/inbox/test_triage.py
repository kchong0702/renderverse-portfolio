from base64 import urlsafe_b64encode
from uuid import uuid4

from src.clients.google.client import MISSING_SCOPE
from tests.conftest import PREFIX, a2a_sent, a2a_task, connect_google

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
        "Your offer": _triaged("offer", decide_by="2026-11-14"),
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
        ("m2", "offer", "2026-11-14", None),
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
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [_triaged("interview", interview=INTERVIEW)]

    await client.get(INBOX)
    await client.get(INBOX)

    assert google.created == [
        {
            "summary": "Final round",
            "start": {"dateTime": "2030-11-12T02:00:00Z"},
            "end": {"dateTime": "2030-11-12T03:00:00Z"},
            "location": "https://meet.google.com/abc",
        }
    ]


async def test_interviews_are_not_added_with_the_rule_off(client, google, harness):
    await connect_google(client)
    await client.patch(
        f"{PREFIX}/settings", json={"automation": {"add_interview_invites": False}}
    )
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [_triaged("interview", interview=INTERVIEW)]

    response = await client.get(INBOX)

    assert response.json()["messages"][0]["state"] == "interview"
    assert google.created == []


async def test_a_past_interview_is_not_added(client, google, harness):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "Thanks.")}
    past = INTERVIEW | {"start": "2020-11-12T10:00:00+08:00"}
    harness.outcomes = [_triaged("interview", interview=past)]

    await client.get(INBOX)

    assert google.created == []


async def test_an_interview_waits_for_a_grant_that_adds_events(client, google, harness):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "t-1", "Final round", "See you then.")}
    harness.outcomes = [_triaged("interview", interview=INTERVIEW)]
    google.read_only = True

    refused = await client.get(INBOX)
    google.read_only = False
    added = await client.get(INBOX)

    assert refused.status_code == 409
    assert refused.json() == {"detail": MISSING_SCOPE}
    assert added.status_code == 200
    assert len(harness.received) == 1
    assert [event["summary"] for event in google.created] == ["Final round"]
