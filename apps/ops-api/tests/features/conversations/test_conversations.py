from urllib.parse import parse_qs

from sqlalchemy import select

from src.core.auth.models import AuthSession, User
from src.core.auth.service import AuthService
from src.core.config import get_settings
from src.features.conversations.models import AgentSession, AgentThread, ThreadMessage
from tests.conftest import (
    OWNER,
    PREFIX,
    a2a_replied,
    a2a_task,
    a2a_turn,
    ask,
    interrupt_part,
    sent_messages,
    sse_events,
    stream_status,
    thread_of,
)

AGENT = f"{PREFIX}/agent"

RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}}
        ]
    },
}


async def _messages(client, thread: str, **params) -> dict:
    return (
        await client.get(f"{AGENT}/threads/{thread}/messages", params=params)
    ).json()


async def test_career_director_has_one_thread_and_career_consultant_one_per_document(
    client,
):
    document = (
        await client.post(f"{PREFIX}/documents", json={"title": "CV", "body": RESUME})
    ).json()
    director = (await client.get(f"{AGENT}/sessions/career-director")).json()
    consultant = (
        await client.get(
            f"{AGENT}/sessions/career-consultant",
            params={"document_id": document["id"]},
        )
    ).json()

    assert director["agent"] == "career-director"
    assert consultant["agent"] == "career-consultant"
    assert director["thread_id"] != consultant["thread_id"]
    assert (await client.get(f"{AGENT}/sessions/career-director")).json() == director
    assert (
        await client.get(f"{AGENT}/sessions/productivity-assistant")
    ).status_code == 422


async def test_clearing_starts_a_new_thread_and_keeps_the_old_ones_messages(
    client, harness
):
    old = await thread_of(client)
    await ask(client, harness, "Hi", *a2a_replied("Hello."))

    response = await client.post(f"{AGENT}/sessions/career-director/threads")

    assert response.status_code == 201
    new = response.json()["thread_id"]
    assert new != old
    assert await thread_of(client) == new
    assert await _messages(client, new) == {"messages": [], "has_more": False}
    assert [m["text"] for m in (await _messages(client, old))["messages"]] == [
        "Hi",
        "Hello.",
    ]


async def test_a_cleared_thread_takes_no_new_message(client, harness):
    old = await thread_of(client)
    await client.post(f"{AGENT}/sessions/career-director/threads")
    harness.outcomes = a2a_replied("Hello.")

    response = await client.post(f"{AGENT}/threads/{old}/messages", json={"text": "Hi"})

    assert response.status_code == 409
    assert harness.received == []
    assert (await _messages(client, old))["messages"] == []


async def test_a_turn_keeps_the_users_message_and_the_agents_answer(client, harness):
    thread = await thread_of(client)
    await ask(
        client,
        harness,
        "Find me jobs",
        *a2a_turn(
            stream_status(
                "WORKING",
                [
                    {
                        "data": {
                            "step": {
                                "id": "call-1",
                                "parent": None,
                                "name": "find_jobs",
                                "status": "done",
                            }
                        }
                    }
                ],
            ),
            stream_status("COMPLETED", [{"text": "Two fit."}], "reply-1"),
        ),
    )

    user, agent = (await _messages(client, thread))["messages"]
    assert (user["role"], user["text"], user["agent"], user["steps"]) == (
        "user",
        "Find me jobs",
        None,
        None,
    )
    assert user["id"] == sent_messages(harness)[0]["message"]["messageId"]
    assert agent == {
        "id": "reply-1",
        "role": "agent",
        "text": "Two fit.",
        "created_at": agent["created_at"],
        "document_id": None,
        "agent": "career-director",
        "changesets": [],
        "steps": [
            {
                "id": "call-1",
                "parent": None,
                "name": "find_jobs",
                "status": "done",
                "detail": None,
                "document_id": None,
            }
        ],
        "failure": None,
    }


async def test_a_reply_read_again_after_a_reconnect_is_kept_once(client, harness):
    thread = await thread_of(client)
    completed = a2a_task("COMPLETED", status_parts=[{"text": "Done."}])["result"]
    completed["task"]["status"]["message"]["messageId"] = "reply-1"

    response = await ask(
        client,
        harness,
        "Hi",
        *a2a_turn(),
        {"result": completed["task"]},
    )

    assert [e["status"] for e in sse_events(response)] == [
        "started",
        "reconnecting",
        "reconnected",
        "completed",
    ]
    assert [m["id"] for m in (await _messages(client, thread))["messages"]][1:] == [
        "reply-1"
    ]


async def test_messages_page_back_from_the_newest_oldest_first(client, harness):
    thread = await thread_of(client)
    for n in range(3):
        await ask(client, harness, f"Q{n}", *a2a_replied(f"A{n}", f"reply-{n}"))

    latest = await _messages(client, thread, limit=4)
    older = await _messages(client, thread, limit=4, before=latest["messages"][0]["id"])

    assert [m["text"] for m in latest["messages"]] == ["Q1", "A1", "Q2", "A2"]
    assert latest["has_more"] is True
    assert [m["text"] for m in older["messages"]] == ["Q0", "A0"]
    assert older["has_more"] is False
    missing = await client.get(
        f"{AGENT}/threads/{thread}/messages", params={"before": "nope"}
    )
    assert missing.status_code == 404


async def test_another_users_thread_is_not_found(app, client, harness):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.flush()
        await AuthService(session, get_settings().auth).create_session(other, "UTC")
        theirs = await session.scalar(
            select(AgentThread.id).where(AgentThread.user_id == other.id)
        )
        await session.commit()

    read = await client.get(f"{AGENT}/threads/{theirs}/messages")
    sent = await client.post(f"{AGENT}/threads/{theirs}/messages", json={"text": "Hi"})

    assert (read.status_code, sent.status_code) == (404, 404)
    assert harness.received == []


async def test_a_new_message_carries_when_and_where_the_user_wrote_it(client, harness):
    thread = await thread_of(client)

    await ask(client, harness, "Hi", *a2a_replied("Hello.", "reply-1"))

    [user, _] = (await _messages(client, thread))["messages"]
    [sent] = sent_messages(harness)
    assert sent["message"]["messageId"] == user["id"]
    assert sent["message"]["metadata"] == {
        "created_at": user["created_at"].replace("+00:00", "Z"),
        "timezone": "UTC",
    }


async def test_the_summary_is_read_and_edited_through_the_harness(client, harness):
    thread = await thread_of(client)
    summary = f"{AGENT}/threads/{thread}/summary"

    empty = (await client.get(summary)).json()
    refused = await client.put(summary, json={"summary": "Mine"})
    harness.summaries[thread] = {"summary": "Looking for backend roles."}
    edited = (
        await client.put(summary, json={"summary": "Backend roles in KL."})
    ).json()

    assert empty == {"summary": None}
    assert refused.status_code == 404
    assert edited == {"summary": "Backend roles in KL."}
    assert parse_qs(harness.received[-1].url.query.decode()) == {
        "agent": ["career-director"]
    }


async def test_a_summary_edit_waits_for_the_threads_reply_to_finish(client, harness):
    thread = await thread_of(client)
    harness.summaries[thread] = {"summary": "Looking for backend roles."}
    harness.busy.add(thread)

    refused = await client.put(
        f"{AGENT}/threads/{thread}/summary", json={"summary": "Mine"}
    )

    assert refused.status_code == 409
    assert harness.summaries[thread] == {"summary": "Looking for backend roles."}


async def test_signing_in_records_the_browsers_zone_and_opens_both_sessions(
    auth_app, auth_client, harness
):
    async with auth_app.state.session_factory() as session:
        await AuthService(session, get_settings().auth).set_password(OWNER, "p" * 12)
        await session.commit()

    refused = await auth_client.post(
        f"{PREFIX}/auth/password",
        json={"email": OWNER, "password": "p" * 12, "timezone": "Mars/Olympus"},
    )
    await auth_client.post(
        f"{PREFIX}/auth/password",
        json={"email": OWNER, "password": "p" * 12, "timezone": "Asia/Kuala_Lumpur"},
    )
    await ask(auth_client, harness, "Hi", *a2a_replied("Hello."))

    assert refused.status_code == 422
    async with auth_app.state.session_factory() as session:
        [zone] = await session.scalars(select(AuthSession.timezone))
        user_zone = await session.scalar(
            select(ThreadMessage.timezone).where(ThreadMessage.role == "user")
        )
        agents = set(await session.scalars(select(AgentSession.agent)))
    assert zone == user_zone == "Asia/Kuala_Lumpur"
    assert agents == {"career-director", "career-consultant"}


async def test_signing_in_with_a_provider_records_the_zone_the_login_carried(
    auth_app, auth_client
):
    await auth_client.get(f"{PREFIX}/auth/google/login?timezone=Europe/London")
    await auth_client.get(f"{PREFIX}/auth/google/callback")

    async with auth_app.state.session_factory() as session:
        [zone] = await session.scalars(select(AuthSession.timezone))
    assert zone == "Europe/London"
    assert (
        await auth_client.get(f"{AGENT}/sessions/career-director")
    ).status_code == 200
    bad = await auth_client.get(f"{PREFIX}/auth/google/login?timezone=Nowhere")
    assert bad.status_code == 422


async def test_a_tool_pause_answer_carries_each_interrupt_id(client, harness):
    await ask(
        client,
        harness,
        "Hi",
        *a2a_turn(
            stream_status(
                "INPUT_REQUIRED",
                [interrupt_part({"execute_tool": "weather"}, "i-7")],
            )
        ),
        *a2a_replied("Hello."),
    )

    [part] = sent_messages(harness)[1]["message"]["parts"]
    assert part["metadata"] == {"interrupt_id": "i-7"}
    assert sent_messages(harness)[1]["configuration"] == {"returnImmediately": True}
