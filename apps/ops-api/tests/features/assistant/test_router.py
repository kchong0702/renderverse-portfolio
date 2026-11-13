import json
from datetime import datetime
from uuid import UUID, uuid4

import httpx2
from document_schema import AnyDocument
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import select

from src.clients.ezcareer import Answer, EzcareerClient
from src.clients.ezcareer.schemas import Completed, DataRequest, Started
from src.core.auth.models import User
from src.core.config import get_settings
from src.core.stores import AgentModelCall
from src.features.documents.models import Document, DocumentChangeset
from tests.conftest import (
    PREFIX,
    a2a_sent,
    sse_events,
    sse_ids,
    stream_chunk,
    stream_status,
    stream_task,
)

ASSISTANT = f"{PREFIX}/assistant"
CHAT_ID = "9b2d6f3e-1c4a-4e8b-9f0d-2a7c5e1b3d4f"
CHAT = f"{ASSISTANT}/chats/{CHAT_ID}"
OTHER_CHAT_ID = "1f0e3c2a-7b6d-4c5e-8a9f-0b1c2d3e4f5a"

WIDGET = {
    "label": "May I go ahead? Save the job to your list.",
    "submit_btn": "Confirm",
    "cancel_btn": "Cancel",
}

STEP = {"id": "call-1", "parent": None, "name": "find_jobs"}


def _replied(text: str) -> list[dict]:
    """A turn that only replies with text"""
    return [
        stream_task(),
        stream_chunk("a-1", "career-director", {"text": text}),
        stream_status("COMPLETED"),
    ]


async def _ignore_usage(*args: object) -> None:
    """Drops a model call's usage"""


async def test_a_message_streams_career_directors_turn_with_the_profile(
    client, harness
):
    await client.patch(f"{PREFIX}/preferences", json={"work_modes": ["remote"]})
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [
        [
            stream_task(),
            stream_status("WORKING"),
            stream_status(
                "WORKING", [{"data": {"step": STEP | {"status": "running"}}}]
            ),
            stream_chunk("thinking-1", "thinking", {"text": "Look for remote roles."}),
            stream_status("WORKING", [{"data": {"step": STEP | {"status": "done"}}}]),
            stream_chunk("text-2", "text", {"text": "Two "}),
            stream_chunk("text-2", "text", {"text": "fit."}),
            stream_chunk("a-1", "career-director", {"text": "Two fit."}),
            stream_status("COMPLETED"),
        ]
    ]

    response = await client.post(
        f"{CHAT}/messages", json={"text": "Find me remote jobs"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "step", "step": STEP | {"status": "running", "detail": None}},
        {"status": "thinking", "turn": "thinking-1", "text": "Look for remote roles."},
        {"status": "step", "step": STEP | {"status": "done", "detail": None}},
        {"status": "text", "turn": "text-2", "text": "Two "},
        {"status": "text", "turn": "text-2", "text": "fit."},
        {"status": "completed", "reply": "Two fit."},
    ]
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/career-director"
    assert request.headers["A2A-Version"] == "1.0"
    assert request.headers["Accept"] == "text/event-stream"
    [sent] = a2a_sent(harness)
    assert sent["method"] == "SendStreamingMessage"
    message = sent["params"]["message"]
    assert message["role"] == "ROLE_USER"
    assert message["contextId"] == f"{me['id']}:{CHAT_ID}"
    assert "taskId" not in message
    assert message["parts"] == [
        {"text": "Find me remote jobs"},
        {"data": agent_profile},
    ]
    assert "metadata" not in sent["params"]


async def test_each_run_carries_the_users_model_on_the_request(client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": WIDGET}])],
        _replied("Saved it."),
    ]

    await client.post(f"{CHAT}/messages", json={"text": "Save it"})
    await client.post(f"{CHAT}/tasks/task-1/answer", json={"accept": True})

    first, resume = (sent["params"] for sent in a2a_sent(harness))
    assert first["metadata"] == {"model": model}
    assert resume["metadata"] == first["metadata"]
    assert "metadata" not in first["message"]


async def test_each_chat_runs_in_a_context_of_its_own(client, harness):
    harness.outcomes = [_replied("One."), _replied("Two.")]
    me = (await client.get(f"{PREFIX}/me")).json()

    await client.post(f"{CHAT}/messages", json={"text": "Hi"})
    await client.post(
        f"{ASSISTANT}/chats/{OTHER_CHAT_ID}/messages", json={"text": "Hi"}
    )

    assert [sent["params"]["message"]["contextId"] for sent in a2a_sent(harness)] == [
        f"{me['id']}:{CHAT_ID}",
        f"{me['id']}:{OTHER_CHAT_ID}",
    ]


async def test_a_widget_is_shown_and_the_answer_streams_the_rest_of_the_turn(
    client, harness
):
    harness.outcomes = [
        [stream_task(), stream_status("INPUT_REQUIRED", [{"data": WIDGET}])],
        [
            stream_status("WORKING"),
            stream_chunk("a-1", "career-director", {"text": "Saved it."}),
            stream_status("COMPLETED"),
        ],
    ]

    asked = await client.post(f"{CHAT}/messages", json={"text": "Save it"})
    done = await client.post(f"{CHAT}/tasks/task-1/answer", json={"accept": True})

    assert sse_events(asked)[-1] == {
        "status": "input_required",
        "task_id": "task-1",
        "widget": {
            "label": WIDGET["label"],
            "input_value": None,
            "input_placeholder": None,
            "submit_btn": "Confirm",
            "cancel_btn": "Cancel",
            "choose": None,
            "kind": None,
        },
    }
    assert sse_events(done) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "completed", "reply": "Saved it."},
    ]
    first, resume = (sent["params"]["message"] for sent in a2a_sent(harness))
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == first["contextId"]
    assert resume["parts"] == [{"data": {"input": None, "accept": True}}]


async def test_a_failed_task_streams_its_reason(client, harness):
    harness.outcomes = [
        [
            stream_task(),
            stream_status("FAILED", [{"text": "Ran out of steps before finishing"}]),
        ]
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "Ran out of steps before finishing",
        "next": None,
    }


async def test_a_stopped_turn_streams_that_it_was_cancelled(client, harness):
    harness.outcomes = [[stream_task(), stream_status("CANCELED")]]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert sse_events(response)[-1] == {"status": "cancelled"}


async def test_a_step_streams_its_detail(client, harness):
    done = STEP | {"status": "done", "detail": "1 cover letter"}
    harness.outcomes = [
        [stream_task(), stream_status("WORKING", [{"data": {"step": done}}])]
        + _replied("Found it.")[1:]
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert sse_events(response)[1] == {"status": "step", "step": done}


async def test_a_refusal_streams_the_screen_to_add_what_it_lacks(client, harness):
    portfolio = {"label": "Add a fact in Portfolio", "screen": "portfolio"}
    harness.outcomes = [
        [
            stream_task(),
            stream_status(
                "FAILED",
                [{"text": "No fact backs this claim."}, {"data": {"next": portfolio}}],
            ),
        ]
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "No fact backs this claim.",
        "next": portfolio,
    }


async def test_answering_a_task_the_harness_lost_streams_its_reason(client, harness):
    reason = "Task task-1 not found"
    harness.outcomes = [[{"error": {"code": -32001, "message": reason}}]]

    response = await client.post(
        f"{CHAT}/tasks/task-1/answer", json={"input": "The queue one"}
    )

    assert sse_events(response) == [
        {"status": "failed", "reason": reason, "next": None}
    ]


async def test_an_unreachable_harness_streams_a_clear_reason(client, harness):
    harness.down = True

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert response.status_code == 200
    assert sse_events(response) == [
        {
            "status": "failed",
            "reason": "ezcareer-harness did not answer career-director; try again later",
            "next": None,
        }
    ]


async def test_a_reply_ops_api_cannot_read_streams_the_same_reason(client, harness):
    harness.outcomes = [
        [stream_task(), stream_chunk("a-1", "career-director", {"data": 1})]
    ]
    harness.outcomes[0].append(stream_status("COMPLETED"))

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "ezcareer-harness did not answer career-director; try again later",
        "next": None,
    }


async def test_stop_cancels_the_chats_running_task(client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()
    task = {
        "id": "task-1",
        "contextId": f"{me['id']}:{CHAT_ID}",
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}, {"result": task}]

    response = await client.post(f"{CHAT}/tasks/task-1/cancel")

    assert response.status_code == 204
    assert [(s["method"], s["params"]) for s in a2a_sent(harness)] == [
        ("GetTask", {"id": "task-1"}),
        ("CancelTask", {"id": "task-1"}),
    ]


async def test_stop_leaves_another_chats_task_alone(client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()
    task = {
        "id": "task-1",
        "contextId": f"{me['id']}:{OTHER_CHAT_ID}",
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}]

    response = await client.post(f"{CHAT}/tasks/task-1/cancel")

    assert response.status_code == 404
    assert [s["method"] for s in a2a_sent(harness)] == ["GetTask"]


async def test_a_stream_closed_before_the_turn_ends_cancels_its_task(harness):
    cancelled = {"id": "task-1", "status": {"state": "TASK_STATE_CANCELED"}}
    harness.outcomes = [
        [stream_task(), stream_status("WORKING")],
        {"result": cancelled},
    ]
    ezcareer = EzcareerClient(
        get_settings().ezcareer, _ignore_usage, httpx2.MockTransport(harness)
    )
    run = ezcareer.stream(
        "career-director",
        str,
        user_id=uuid4(),
        context_id="u:c",
        data=Answer(),
        metadata=None,
    )

    assert await anext(run) == Started(task_id="task-1")
    await run.aclose()

    assert [(s["method"], s["params"].get("id")) for s in a2a_sent(harness)] == [
        ("SendStreamingMessage", None),
        ("CancelTask", "task-1"),
    ]


async def test_a_turn_sends_event_ids_and_a_retry_hint(client, harness):
    harness.outcomes = [_replied("Hi.")]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    run_id = sse_ids(response)[0].partition(":")[0]
    assert sse_ids(response) == [f"{run_id}:1", f"{run_id}:2"]
    assert "retry: 2000" in response.text.splitlines()


async def test_a_broken_stream_resumes_after_the_last_event_it_got(client, harness):
    harness.outcomes = [
        [
            stream_task(),
            stream_chunk("text-1", "text", {"text": "Two "}),
            stream_chunk("text-1", "text", {"text": "fit."}),
            stream_chunk("a-1", "career-director", {"text": "Two fit."}),
            stream_status("COMPLETED"),
        ]
    ]
    first = await client.post(f"{CHAT}/messages", json={"text": "Hi"})
    second_id = sse_ids(first)[1]

    resumed = await client.get(f"{CHAT}/stream", headers={"Last-Event-ID": second_id})
    replayed = await client.get(f"{CHAT}/stream")

    assert sse_events(resumed) == sse_events(first)[2:]
    assert sse_ids(resumed) == sse_ids(first)[2:]
    assert sse_events(replayed) == sse_events(first)


async def test_nothing_resumes_from_another_run_or_an_idle_chat(client, harness):
    harness.outcomes = [_replied("Hi.")]
    await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    foreign = await client.get(
        f"{CHAT}/stream", headers={"Last-Event-ID": "0123456789abcdef:1"}
    )
    idle = await client.get(f"{ASSISTANT}/chats/{OTHER_CHAT_ID}/stream")

    assert foreign.status_code == 404
    assert idle.status_code == 404


async def test_a_chat_takes_no_new_message_while_its_turn_runs(app, client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()
    await app.state.container.store().create(
        UUID(me["id"]), f"{me['id']}:{CHAT_ID}", "career-director"
    )

    response = await client.post(f"{CHAT}/messages", json={"text": "Again"})

    assert response.status_code == 409
    assert harness.received == []


class _Documents(BaseModel):
    documents: list[str]


async def test_a_stream_answers_the_data_requests_its_run_pauses_with(harness):
    asked: list[DataRequest] = []

    async def answer(request: DataRequest) -> _Documents:
        asked.append(request)
        return _Documents(documents=["Résumé for Northwind"])

    harness.outcomes = [
        [
            stream_task(),
            stream_status(
                "INPUT_REQUIRED", [{"data": {"fetch": "documents", "name": "nw"}}]
            ),
        ],
        [
            stream_status("WORKING"),
            stream_chunk("a-1", "career-director", {"text": "Found it."}),
            stream_status("COMPLETED"),
        ],
    ]
    ezcareer = EzcareerClient(
        get_settings().ezcareer, _ignore_usage, httpx2.MockTransport(harness)
    )

    events = [
        event
        async for event in ezcareer.stream(
            "career-director",
            str,
            user_id=uuid4(),
            context_id="u:c",
            data=Answer(),
            metadata=None,
            answer_data_request=answer,
        )
    ]

    assert events == [Started(task_id="task-1"), Completed(reply="Found it.")]
    assert [r.model_dump() for r in asked] == [{"fetch": "documents", "name": "nw"}]
    resume = a2a_sent(harness)[1]["params"]["message"]
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == "u:c"
    assert resume["parts"] == [{"data": {"documents": ["Résumé for Northwind"]}}]


async def test_a_data_request_ops_does_not_know_is_answered_with_why(client, harness):
    harness.outcomes = [
        [
            stream_task(),
            stream_status("INPUT_REQUIRED", [{"data": {"fetch": "weather"}}]),
        ],
        _replied("I can't check the weather."),
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Is it sunny?"})

    assert sse_events(response)[-1] == {
        "status": "completed",
        "reply": "I can't check the weather.",
    }
    [part] = a2a_sent(harness)[1]["params"]["message"]["parts"]
    assert part == {"data": {"error": "Ops can't answer weather"}}


async def test_a_blocking_run_answers_its_data_requests_too(harness):
    async def answer(request: DataRequest) -> _Documents:
        return _Documents(documents=[request.model_dump()["name"]])

    paused = {
        "result": {
            "task": {
                "id": "task-1",
                "status": {
                    "state": "TASK_STATE_INPUT_REQUIRED",
                    "message": {
                        "messageId": "m",
                        "role": "ROLE_AGENT",
                        "parts": [{"data": {"fetch": "documents", "name": "nw"}}],
                    },
                },
            }
        }
    }
    done = {
        "result": {
            "task": {
                "id": "task-1",
                "status": {"state": "TASK_STATE_COMPLETED"},
                "artifacts": [
                    {
                        "artifactId": "a",
                        "name": "edit-document",
                        "parts": [{"text": "ok"}],
                    }
                ],
            }
        }
    }
    harness.outcomes = [paused, done]
    ezcareer = EzcareerClient(
        get_settings().ezcareer, _ignore_usage, httpx2.MockTransport(harness)
    )

    run = await ezcareer.send(
        "edit-document",
        str,
        user_id=uuid4(),
        context_id="u:c",
        data=Answer(),
        metadata=None,
        answer_data_request=answer,
    )

    assert run == Completed(reply="ok")
    assert a2a_sent(harness)[1]["params"]["message"]["parts"] == [
        {"data": {"documents": ["nw"]}}
    ]


USAGE = {
    "provider": "claude",
    "model": "claude-sonnet-5-5",
    "agent": "career-director",
    "node": "model",
    "input_tokens": 1000.0,
    "output_tokens": 200.0,
    "cache_read_tokens": 600.0,
    "cache_write_tokens": 100.0,
    "reasoning_tokens": 50.0,
    "latency_ms": 1200.0,
    "stop_reason": "end_turn",
    "request_id": None,
}


async def test_a_turn_keeps_each_model_calls_usage_as_its_user_and_never_streams_it(
    app, client, harness
):
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [
        [
            stream_task(),
            stream_status("WORKING", [{"data": {"usage": USAGE}}]),
            stream_chunk("a-1", "career-director", {"text": "Hi."}),
            stream_status("COMPLETED"),
        ]
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert [e["status"] for e in sse_events(response)] == ["started", "completed"]
    async with app.state.container.session_factory()() as session:
        [call] = (await session.scalars(select(AgentModelCall))).all()
    assert (call.user_id, call.thread_id, call.task_id) == (
        UUID(me["id"]),
        f"{me['id']}:{CHAT_ID}",
        "task-1",
    )
    assert (call.agent, call.node, call.provider, call.model) == (
        "career-director",
        "model",
        "claude",
        "claude-sonnet-5-5",
    )
    assert (
        call.input_tokens,
        call.output_tokens,
        call.cache_read_tokens,
        call.cache_write_tokens,
        call.reasoning_tokens,
        call.latency_ms,
        call.stop_reason,
        call.provider_request_id,
    ) == (1000, 200, 600, 100, 50, 1200, "end_turn", None)
    assert call.created_by == f"user:{me['id']}"


async def test_a_blocking_run_keeps_each_usage_its_history_reports_once(harness):
    kept: list[tuple[str, str, str]] = []

    async def record(user_id: UUID, thread_id: str, task_id: str, usage) -> None:
        kept.append((thread_id, task_id, usage.model))

    async def answer(request: DataRequest) -> _Documents:
        return _Documents(documents=[])

    def usage(message_id: str, model: str) -> dict:
        return {
            "messageId": message_id,
            "role": "ROLE_AGENT",
            "parts": [{"data": {"usage": {**USAGE, "model": model}}}],
        }

    asked = {
        "messageId": "ask",
        "role": "ROLE_AGENT",
        "parts": [{"data": {"fetch": "documents"}}],
    }
    paused = {
        "result": {
            "task": {
                "id": "task-1",
                "status": {"state": "TASK_STATE_INPUT_REQUIRED", "message": asked},
                "history": [usage("u-1", "first")],
            }
        }
    }
    done = {
        "result": {
            "task": {
                "id": "task-1",
                "status": {"state": "TASK_STATE_COMPLETED"},
                "artifacts": [{"name": "edit-document", "parts": [{"text": "ok"}]}],
                "history": [usage("u-1", "first"), asked, usage("u-2", "second")],
            }
        }
    }
    harness.outcomes = [paused, done]
    ezcareer = EzcareerClient(
        get_settings().ezcareer, record, httpx2.MockTransport(harness)
    )

    run = await ezcareer.send(
        "edit-document",
        str,
        user_id=uuid4(),
        context_id="u:c",
        data=Answer(),
        metadata=None,
        answer_data_request=answer,
    )

    assert run == Completed(reply="ok")
    assert kept == [("u:c", "task-1", "first"), ("u:c", "task-1", "second")]


RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}},
            {"kind": "summary", "id": "sum", "text": {"html": "Backend engineer."}},
        ]
    },
}

TAILOR = {
    "id": "tailor-1",
    "agent": "career-consultant",
    "reason": "Match the Northwind Labs posting.",
    "edits": [
        {
            "kind": "update_field",
            "path": "blocks/sum/text",
            "value": {"html": "Backend engineer, 7 years.", "src": ["fact:role-1"]},
        }
    ],
}


def _proposed(document_id: str) -> list[dict]:
    """A turn where career-director proposes edits to a document, then replies"""
    return [
        stream_task(),
        stream_chunk("notes-1", "notes", {"data": {"seen": 1}}),
        stream_chunk(
            "changeset-1",
            "changeset",
            {"data": {"document_id": document_id, "changeset": TAILOR}},
        ),
        stream_chunk("a-1", "career-director", {"text": "Review my edits."}),
        stream_status("COMPLETED"),
    ]


async def test_edits_career_director_proposes_are_stored_and_announced(client, harness):
    document = (
        await client.post(
            f"{PREFIX}/documents", json={"title": "Master résumé", "body": RESUME}
        )
    ).json()
    harness.outcomes = [_proposed(document["id"])]

    response = await client.post(f"{CHAT}/messages", json={"text": "Tailor it"})

    [stored] = (
        await client.get(f"{PREFIX}/documents/{document['id']}/changesets")
    ).json()
    assert stored["changeset"]["id"] == "tailor-1"
    assert stored["changeset"]["status"] == "pending"
    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {
            "status": "changeset",
            "document_id": document["id"],
            "title": "Master résumé",
            "changeset_id": stored["id"],
            "edits": 1,
        },
        {"status": "completed", "reply": "Review my edits."},
    ]


async def test_edits_to_another_users_document_are_skipped(app, client, harness):
    async with app.state.session_factory() as session:
        other = User(email="other@example.com")
        session.add(other)
        await session.flush()
        theirs = Document(
            user_id=other.id,
            kind="resume",
            title="Theirs",
            body=TypeAdapter(AnyDocument).validate_python(RESUME),
        )
        session.add(theirs)
        await session.commit()
    harness.outcomes = [_proposed(str(theirs.id))]

    response = await client.post(f"{CHAT}/messages", json={"text": "Tailor it"})

    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "completed", "reply": "Review my edits."},
    ]
    async with app.state.session_factory() as session:
        assert (await session.scalars(select(DocumentChangeset))).all() == []


ACME = {
    "kind": "role",
    "title": "Backend Engineer",
    "organisation": "Acme Corp",
    "start": "2020-01",
    "end": "present",
    "highlights": ["Led payments."],
}


async def _seed(client) -> str:
    """A profile with a headline, one Acme role and a Python skill; the role's fact"""
    await client.patch(
        f"{PREFIX}/profile", json={"name": "Kelvin Chong", "headline": "Engineer"}
    )
    role = (await client.post(f"{PREFIX}/profile/entries", json=ACME)).json()
    await client.post(f"{PREFIX}/profile/skills", json={"name": "Python"})
    return f"role-{role['id']}"


async def _stored(client) -> list[dict]:
    """Everything the Data page reads"""
    return [
        (await client.get(f"{PREFIX}/profile{path}")).json()
        for path in ("", "/entries", "/skills", "/changes", "/imports")
    ]


def _review(*args: dict) -> list[dict]:
    """A turn that pauses for the user to approve update_profile calls"""
    return [
        stream_task(),
        stream_status(
            "INPUT_REQUIRED",
            [
                {
                    "data": {
                        "action_requests": [
                            {"name": "update_profile", "args": a, "description": ""}
                            for a in args
                        ],
                        "review_configs": [
                            {
                                "action_name": "update_profile",
                                "allowed_decisions": ["approve", "reject"],
                            }
                        ],
                    }
                }
            ],
        ),
    ]


def _resumed(*events: dict) -> list[dict]:
    """The rest of a turn after its task is answered"""
    return [stream_status("WORKING"), *events]


def _decisions(harness) -> list[dict]:
    """The decisions ops-api sent on its last message to the harness"""
    [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
    return part["data"]["decisions"]


async def test_a_review_shows_each_change_beside_its_value_in_the_database(
    client, harness
):
    fact = await _seed(client)
    edits = [
        {"kind": "about", "field": "headline", "value": "Staff Engineer"},
        {"kind": "about", "field": "summary", "value": "Builds payments."},
        {
            "kind": "entry",
            "fact": fact,
            "field": "highlights",
            "value": ["Led payments.", "Cut latency."],
        },
        {"kind": "new_skill", "name": "Go", "group": ""},
    ]
    harness.outcomes = [_review({"edits": edits, "source": "Backend résumé"})]
    stored = await _stored(client)

    response = await client.post(f"{CHAT}/messages", json={"text": "Sync me"})

    assert sse_events(response)[-1] == {
        "status": "profile_approval",
        "task_id": "task-1",
        "source": "Backend résumé",
        "rows": [
            {"edit": edits[0], "entry": None, "current": "Engineer"},
            {"edit": edits[1], "entry": None, "current": ""},
            {"edit": edits[2], "entry": "Acme Corp", "current": ["Led payments."]},
            {"edit": edits[3], "entry": None, "current": None},
        ],
    }
    assert await _stored(client) == stored


async def test_approving_resumes_the_turn_and_its_update_saves_every_change(
    client, harness
):
    fact = await _seed(client)
    edits = [
        {"kind": "about", "field": "headline", "value": "Staff Engineer"},
        {"kind": "entry", "fact": fact, "field": "location", "value": "Remote"},
        {"kind": "new_link", "label": "GitHub", "url": "https://github.com/k"},
        {"kind": "new_skill", "name": "Go"},
        {
            "kind": "new_entry",
            "entry": {"kind": "role", "title": "SRE", "start": "2018"},
        },
    ]
    harness.outcomes = [
        _review({"edits": edits}),
        _resumed(
            stream_status(
                "INPUT_REQUIRED",
                [{"data": {"fetch": "profile_update", "edits": edits}}],
            )
        ),
        _resumed(
            stream_chunk("p-1", "profile_updated", {"data": {"saved": 5}}),
            stream_chunk("a-1", "career-director", {"text": "Saved."}),
            stream_status("COMPLETED"),
        ),
    ]
    await client.post(f"{CHAT}/messages", json={"text": "Update me"})

    response = await client.post(
        f"{CHAT}/tasks/task-1/decision", json={"approve": True}
    )

    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "profile_saved", "saved": 5},
        {"status": "completed", "reply": "Saved."},
    ]
    sent = a2a_sent(harness)
    assert sent[1]["params"]["message"]["taskId"] == "task-1"
    assert sent[1]["params"]["message"]["parts"] == [
        {"data": {"decisions": [{"type": "approve"}]}}
    ]
    assert sent[2]["params"]["message"]["parts"] == [{"data": {"saved": 5}}]
    profile, entries, skills, _, _ = await _stored(client)
    assert profile["headline"] == "Staff Engineer"
    assert profile["links"] == [{"label": "GitHub", "url": "https://github.com/k"}]
    assert sorted((e["title"], e["location"], e["start"]) for e in entries) == [
        ("Backend Engineer", "Remote", "2020-01"),
        ("SRE", "", "2018-01"),
    ]
    assert sorted(s["name"] for s in skills) == ["Go", "Python"]


async def test_cancelling_resumes_the_turn_with_a_rejection_and_saves_nothing(
    client, harness
):
    await _seed(client)
    edit = {"kind": "about", "field": "headline", "value": "Staff Engineer"}
    harness.outcomes = [
        _review({"edits": [edit]}),
        _resumed(
            stream_chunk("a-1", "career-director", {"text": "Kept it."}),
            stream_status("COMPLETED"),
        ),
        _review({"edits": [edit]}),
        _resumed(
            stream_chunk("a-1", "career-director", {"text": "Left it."}),
            stream_status("COMPLETED"),
        ),
    ]
    stored = await _stored(client)

    await client.post(f"{CHAT}/messages", json={"text": "Change my headline"})
    with_reason = await client.post(
        f"{CHAT}/tasks/task-1/decision",
        json={"approve": False, "message": "Keep my headline"},
    )
    sent_with_reason = _decisions(harness)
    await client.post(f"{CHAT}/messages", json={"text": "Change my headline"})
    await client.post(f"{CHAT}/tasks/task-1/decision", json={"approve": False})

    assert sse_events(with_reason)[-1] == {"status": "completed", "reply": "Kept it."}
    assert sent_with_reason == [{"type": "reject", "message": "Keep my headline"}]
    assert _decisions(harness) == [{"type": "reject"}]
    assert await _stored(client) == stored


async def test_a_change_that_cannot_be_made_is_rejected_back_to_the_model(
    client, harness
):
    fact = await _seed(client)
    unknown = f"role-{uuid4()}"
    edit = {"kind": "about", "field": "headline", "value": "Staff Engineer"}
    cases = [
        ([{"edits": [{"kind": "about", "field": "nickname", "value": "K"}]}], "field"),
        ([{"edits": [edit], "current": "Engineer"}], "current"),
        (
            [
                {
                    "edits": [
                        {
                            "kind": "entry",
                            "fact": unknown,
                            "field": "title",
                            "value": "X",
                        }
                    ]
                }
            ],
            unknown,
        ),
        (
            [
                {
                    "edits": [
                        {
                            "kind": "entry",
                            "fact": fact,
                            "field": "end",
                            "value": "2019-01",
                        }
                    ]
                }
            ],
            "end must not be before start",
        ),
        (
            [
                {
                    "edits": [
                        {
                            "kind": "entry",
                            "fact": fact,
                            "field": "tools",
                            "value": ["Go"],
                        }
                    ]
                }
            ],
            "Only a project",
        ),
        ([{"edits": [edit]}, {"edits": [edit]}], "one update_profile call"),
    ]
    stored = await _stored(client)

    for actions, reason in cases:
        harness.outcomes = [
            _review(*actions),
            _resumed(
                stream_chunk("a-1", "career-director", {"text": "Let me fix that."}),
                stream_status("COMPLETED"),
            ),
        ]

        response = await client.post(f"{CHAT}/messages", json={"text": "Update me"})

        assert [e["status"] for e in sse_events(response)] == [
            "started",
            "started",
            "completed",
        ]
        decisions = _decisions(harness)
        assert [d["type"] for d in decisions] == ["reject"] * len(actions)
        assert all(reason in d["message"] for d in decisions)
    assert await _stored(client) == stored


RESUME_WITH_ROLES = {
    "kind": "resume",
    "content": {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": {"text": "Kelvin Chong"},
                "headline": {"text": "Staff Engineer"},
            },
            {"kind": "summary", "id": "sum", "text": {"html": "Builds payments."}},
            {
                "kind": "experience",
                "id": "experience",
                "items": [
                    {
                        "id": "acme",
                        "role": {"text": "Backend Engineer"},
                        "company": {"text": "Acme Corp"},
                        "location": {"text": "Kuala Lumpur"},
                        "dates": {
                            "text": {"text": "2020 to now"},
                            "start": "2020-01",
                            "end": "present",
                        },
                        "bullets": [
                            {"id": "b1", "text": {"html": "Led payments."}},
                            {"id": "b2", "text": {"html": "Cut latency."}},
                        ],
                    },
                    {
                        "id": "globex",
                        "role": {"text": "SRE"},
                        "company": {"text": "Globex"},
                        "dates": {
                            "text": {"text": "2018 to 2019"},
                            "start": "2018",
                            "end": "2019",
                        },
                        "bullets": [],
                    },
                ],
            },
            {
                "kind": "skills",
                "id": "skills",
                "items": [
                    {
                        "id": "lang",
                        "label": {"text": "Languages"},
                        "items": [
                            {"id": "py", "text": {"text": "Python"}},
                            {"id": "go", "text": {"text": "Go"}},
                        ],
                    }
                ],
            },
        ]
    },
}


async def test_a_sync_preview_lists_what_syncing_would_change_and_saves_nothing(
    client, harness
):
    fact = await _seed(client)
    document = (
        await client.post(
            f"{PREFIX}/documents",
            json={"title": "Backend résumé", "body": RESUME_WITH_ROLES},
        )
    ).json()
    harness.outcomes = [
        [
            stream_task(),
            stream_status(
                "INPUT_REQUIRED",
                [{"data": {"fetch": "profile_sync", "document_id": document["id"]}}],
            ),
        ],
        _replied("Four changes."),
    ]
    stored = await _stored(client)

    await client.post(f"{CHAT}/messages", json={"text": "Sync with my résumé"})

    [part] = a2a_sent(harness)[1]["params"]["message"]["parts"]
    globex = {
        "kind": "role",
        "title": "SRE",
        "organisation": "Globex",
        "location": "",
        "start": "2018-01",
        "end": "2019-12",
        "summary": "",
        "highlights": [],
        "link": None,
        "code_link": None,
        "tools": [],
    }
    expected = [
        {"kind": "about", "field": "summary", "value": "Builds payments."},
        {"kind": "entry", "fact": fact, "field": "location", "value": "Kuala Lumpur"},
        {"kind": "new_entry", "entry": globex},
        {"kind": "new_skill", "name": "Go", "group": "Languages"},
        {"kind": "about", "field": "headline", "value": "Staff Engineer"},
        {
            "kind": "entry",
            "fact": fact,
            "field": "highlights",
            "value": ["Led payments.", "Cut latency."],
        },
    ]
    assert sorted(part["data"]["edits"], key=json.dumps) == sorted(
        expected, key=json.dumps
    )
    assert await _stored(client) == stored


LETTER = {
    "kind": "cover_letter",
    "content": {
        "blocks": [
            {"kind": "profile", "id": "profile", "name": {"text": "Kelvin Chong"}},
            {
                "kind": "letter",
                "id": "letter",
                "greeting": {"text": "Dear hiring team,"},
                "paragraphs": [{"id": "p1", "text": {"html": "I would apply."}}],
                "closing": {"text": "Yours sincerely,"},
            },
        ]
    },
}


async def test_a_job_run_the_director_asks_for_is_queued_and_answered(client, harness):
    search = {"query": "Staff engineer", "location": None, "posted_within": None}
    harness.outcomes = [
        [
            stream_task(),
            stream_status(
                "INPUT_REQUIRED",
                [
                    {
                        "data": {
                            "fetch": "job_run",
                            "run_after": "2026-11-13T08:00:00+08:00",
                            "search": search,
                        }
                    }
                ],
            ),
        ],
        _replied("Queued for tomorrow at 8."),
        [
            stream_task(),
            stream_status(
                "INPUT_REQUIRED",
                [{"data": {"fetch": "job_run", "run_after": None, "search": None}}],
            ),
        ],
        _replied("One is already queued."),
    ]

    await client.post(f"{CHAT}/messages", json={"text": "Search tomorrow at 8"})
    await client.post(f"{CHAT}/messages", json={"text": "Search now"})

    run = (await client.get(f"{PREFIX}/jobs/runs/latest")).json()
    assert (run["trigger"], run["status"]) == ("agent", "queued")
    assert run["run_after"].startswith("2026-11-13T")
    sent = a2a_sent(harness)
    [answer] = sent[1]["params"]["message"]["parts"]
    assert answer["data"]["id"] == run["id"]
    assert datetime.fromisoformat(
        answer["data"]["run_after"]
    ) == datetime.fromisoformat("2026-11-13T08:00:00+08:00")
    assert sent[3]["params"]["message"]["parts"] == [
        {"data": {"error": "A job agent run is already queued"}}
    ]
    assert harness.received[1].url.path == "/ezcareer/a2a/career-director"


async def test_only_a_resume_or_cv_has_a_sync_preview(client, harness):
    letter = (
        await client.post(
            f"{PREFIX}/documents", json={"title": "Letter", "body": LETTER}
        )
    ).json()
    harness.outcomes = []
    for document_id in (letter["id"], str(uuid4())):
        harness.outcomes += [
            [
                stream_task(),
                stream_status(
                    "INPUT_REQUIRED",
                    [{"data": {"fetch": "profile_sync", "document_id": document_id}}],
                ),
            ],
            _replied("That isn't a résumé."),
        ]

    await client.post(f"{CHAT}/messages", json={"text": "Sync with my letter"})
    await client.post(f"{CHAT}/messages", json={"text": "Sync with that one"})

    sent = a2a_sent(harness)
    assert [s["params"]["message"]["parts"] for s in (sent[1], sent[3])] == [
        [{"data": {"error": "No such résumé or CV"}}]
    ] * 2


async def test_an_update_saves_all_its_changes_or_none(client, harness):
    await _seed(client)
    edits = [
        {"kind": "about", "field": "headline", "value": "Staff Engineer"},
        {"kind": "new_skill", "name": "Go"},
        {"kind": "entry", "fact": f"role-{uuid4()}", "field": "title", "value": "X"},
    ]
    harness.outcomes = [
        [
            stream_task(),
            stream_status(
                "INPUT_REQUIRED",
                [{"data": {"fetch": "profile_update", "edits": edits}}],
            ),
        ],
        _replied("Nothing was saved."),
    ]
    stored = await _stored(client)

    await client.post(f"{CHAT}/messages", json={"text": "Update me"})

    [part] = a2a_sent(harness)[1]["params"]["message"]["parts"]
    assert part == {"data": {"error": f"No such entry {edits[2]['fact']}"}}
    assert await _stored(client) == stored


async def test_an_update_giving_a_role_a_project_field_saves_nothing(client, harness):
    fact = await _seed(client)
    headline = {"kind": "about", "field": "headline", "value": "Staff Engineer"}
    refused = [
        {"kind": "entry", "fact": fact, "field": "link", "value": "https://a.example"},
        {
            "kind": "new_entry",
            "entry": {"kind": "role", "title": "CTO", "tools": ["Go"]},
        },
    ]
    stored = await _stored(client)

    for edit in refused:
        harness.outcomes = [
            [
                stream_task(),
                stream_status(
                    "INPUT_REQUIRED",
                    [{"data": {"fetch": "profile_update", "edits": [headline, edit]}}],
                ),
            ],
            _replied("Nothing was saved."),
        ]

        await client.post(f"{CHAT}/messages", json={"text": "Update me"})

        [part] = a2a_sent(harness)[-1]["params"]["message"]["parts"]
        assert part == {
            "data": {
                "error": "Only a project has a link, code link, tools or a place"
                " on the site"
            }
        }
    assert await _stored(client) == stored
