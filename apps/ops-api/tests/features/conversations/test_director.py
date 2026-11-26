import json
from datetime import datetime
from uuid import UUID, uuid4

import httpx2
from document_schema import AnyDocument
from pydantic import BaseModel, TypeAdapter
from sqlalchemy import select

from src.clients.ezcareer import Answer, EzcareerClient
from src.clients.ezcareer.schemas import Completed, ToolRequest
from src.core.auth.models import User
from src.core.config import get_settings
from src.core.stores import AgentModelCall
from src.features.documents.models import Document, DocumentChangeset
from tests.conftest import (
    PREFIX,
    FakeHarness,
    a2a_accepted,
    a2a_replied,
    a2a_sent,
    a2a_task,
    a2a_turn,
    interrupt_part,
    sent_messages,
    sse_events,
    sse_ids,
    stream_chunk,
    stream_status,
    stream_task,
    thread_of,
    tool_pause,
)

AGENT = f"{PREFIX}/agent"

WIDGET = {
    "label": "May I go ahead? Save the job to your list.",
    "submit_btn": "Confirm",
    "cancel_btn": "Cancel",
}

STEP = {"id": "call-1", "parent": None, "name": "find_jobs", "document_id": None}

GAVE_UP = {
    "status": "failed",
    "reason": "The assistant stopped responding. Send your message again.",
    "next": None,
}

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

ACME = {
    "kind": "role",
    "title": "Backend Engineer",
    "organisation": "Acme Corp",
    "start": "2020-01",
    "end": "present",
    "highlights": ["Led payments."],
}

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


class _Documents(BaseModel):
    documents: list[str]


async def _ignore_usage(*args: object) -> None:
    """Drops a model call's usage"""


async def _send(client, text: str, thread_id: str | None = None):
    """Send the career-director thread, or thread_id, a message on the outcomes
    already queued"""
    return await client.post(
        f"{AGENT}/threads/{thread_id or await thread_of(client)}/messages",
        json={"text": text},
    )


async def _task(client, action: str, body: dict):
    """Answer or decide the career-director thread's task-1"""
    return await client.post(
        f"{AGENT}/threads/{await thread_of(client)}/tasks/task-1/{action}", json=body
    )


def _completed(text: str, message_id: str = "reply-1") -> dict:
    """The status ending a career-director turn with its reply"""
    return stream_status("COMPLETED", [{"text": text}], message_id)


def _paused(request: dict, interrupt_id: str = "interrupt-1") -> dict:
    """The status pausing a turn on a tool request"""
    return stream_status("INPUT_REQUIRED", [interrupt_part(request, interrupt_id)])


def _task_state(state: str, parts: list[dict]) -> dict:
    """What GetTask answers for task-1"""
    return {"result": a2a_task(state, status_parts=parts)["result"]["task"]}


async def test_a_message_streams_career_directors_turn_with_the_profile(
    client, harness
):
    await client.patch(f"{PREFIX}/preferences", json={"work_modes": ["remote"]})
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    thread_id = await thread_of(client)
    harness.outcomes = a2a_turn(
        stream_status("WORKING"),
        stream_status("WORKING", [{"data": {"step": STEP | {"status": "running"}}}]),
        stream_chunk("thinking-1", "thinking", {"text": "Look for remote roles."}),
        stream_status("WORKING", [{"data": {"step": STEP | {"status": "done"}}}]),
        stream_chunk("text-2", "text", {"text": "Two "}),
        stream_chunk("text-2", "text", {"text": "fit."}),
        _completed("Two fit."),
    )

    response = await _send(client, "Find me remote jobs")

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
    assert {request.url.path for request in harness.received} == {
        "/ezcareer/a2a/career-director"
    }
    assert {request.headers["A2A-Version"] for request in harness.received} == {"1.0"}
    [sent] = sent_messages(harness)
    assert sent["configuration"] == {"returnImmediately": True}
    message = sent["message"]
    assert message["role"] == "ROLE_USER"
    assert message["contextId"] == thread_id
    assert "taskId" not in message
    assert message["parts"] == [
        {"text": "Find me remote jobs"},
        {"data": agent_profile},
    ]
    assert "metadata" not in sent
    subscribed = [r for r in a2a_sent(harness) if r["method"] == "SubscribeToTask"]
    assert [r["params"] for r in subscribed] == [{"id": "task-1"}]


async def test_each_message_carries_the_users_model_on_the_request(client, harness):
    model = {"family": "claude", "model": "claude-sonnet-4-5"}
    await client.patch(f"{PREFIX}/settings", json={"ai_model": model})
    harness.outcomes = [
        *a2a_turn(stream_status("INPUT_REQUIRED", [{"data": WIDGET}])),
        *a2a_replied("Saved it."),
    ]

    await _send(client, "Save it")
    await _task(client, "answer", {"accept": True})

    first, resume = sent_messages(harness)
    assert first["metadata"] == {"model": model}
    assert resume["metadata"] == first["metadata"]
    assert first["message"]["metadata"]["timezone"] == "UTC"
    assert "metadata" not in resume["message"]


async def test_each_thread_is_the_context_its_turns_run_in(client, harness):
    harness.outcomes = [*a2a_replied("One."), *a2a_replied("Two.", "reply-2")]
    first = await thread_of(client)
    await _send(client, "Hi", first)
    cleared = await client.post(f"{AGENT}/sessions/career-director/threads")
    second = cleared.json()["thread_id"]
    await _send(client, "Hi", second)

    assert cleared.status_code == 201
    assert first != second
    assert [m["message"]["contextId"] for m in sent_messages(harness)] == [
        first,
        second,
    ]


async def test_a_widget_is_shown_and_the_answer_streams_the_rest_of_the_turn(
    client, harness
):
    harness.outcomes = [
        *a2a_turn(stream_status("INPUT_REQUIRED", [{"data": WIDGET}])),
        *a2a_replied("Saved it."),
    ]

    asked = await _send(client, "Save it")
    done = await _task(client, "answer", {"accept": True})

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
    first, resume = (sent["message"] for sent in sent_messages(harness))
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == first["contextId"]
    assert resume["parts"] == [{"data": {"input": None, "accept": True}}]


async def test_a_message_sent_while_a_widget_waits_answers_it(client, harness):
    harness.outcomes = [
        *a2a_turn(stream_status("INPUT_REQUIRED", [{"data": WIDGET}], "ask-1")),
        *a2a_replied("Saved it."),
    ]

    await _send(client, "Save it")
    done = await _send(client, "Save it as Staff Engineer")

    assert sse_events(done)[-1] == {"status": "completed", "reply": "Saved it."}
    resume = sent_messages(harness)[-1]["message"]
    assert resume["taskId"] == "task-1"
    assert resume["parts"] == [
        {"data": {"input": "Save it as Staff Engineer", "accept": True}}
    ]
    page = await client.get(f"{AGENT}/threads/{await thread_of(client)}/messages")
    assert [(m["role"], m["text"]) for m in page.json()["messages"]][-2:] == [
        ("user", "Save it as Staff Engineer"),
        ("agent", "Saved it."),
    ]


async def test_an_answer_is_kept_as_the_users_message(client, harness):
    harness.outcomes = [
        *a2a_turn(stream_status("INPUT_REQUIRED", [{"data": WIDGET}], "ask-1")),
        *a2a_replied("Saved it."),
    ]

    await _send(client, "Save it")
    await _task(client, "answer", {"accept": True})

    page = await client.get(f"{AGENT}/threads/{await thread_of(client)}/messages")
    assert [(m["role"], m["text"]) for m in page.json()["messages"]][-2:] == [
        ("user", "Submitted"),
        ("agent", "Saved it."),
    ]


async def test_a_failed_task_streams_its_reason(client, harness):
    harness.outcomes = a2a_turn(
        stream_status("FAILED", [{"text": "Ran out of steps before finishing"}])
    )

    response = await _send(client, "Hi")

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "Ran out of steps before finishing",
        "next": None,
    }


async def test_a_task_that_ended_before_it_was_followed_streams_how_it_ended(
    client, harness
):
    harness.outcomes = [
        a2a_accepted(),
        {
            "jsonrpc": "2.0",
            "id": "1",
            "error": {"code": -32004, "message": "Task task-1 is in terminal state"},
        },
        _task_state("FAILED", [{"text": "Invalid input"}]),
    ]

    response = await _send(client, "Hi")

    assert [event["status"] for event in sse_events(response)] == [
        "started",
        "failed",
    ]
    assert sse_events(response)[-1]["reason"] == "Invalid input"


async def test_a_stopped_turn_streams_that_it_was_cancelled(client, harness):
    harness.outcomes = a2a_turn(stream_status("CANCELED"))

    response = await _send(client, "Hi")

    assert sse_events(response)[-1] == {"status": "cancelled"}


async def test_a_step_streams_its_detail(client, harness):
    done = STEP | {"status": "done", "detail": "1 cover letter"}
    harness.outcomes = a2a_turn(
        stream_status("WORKING", [{"data": {"step": done}}]), _completed("Found it.")
    )

    response = await _send(client, "Hi")

    assert sse_events(response)[1] == {"status": "step", "step": done}


async def test_a_refusal_streams_the_screen_to_add_what_it_lacks(client, harness):
    portfolio = {"label": "Add a fact in Portfolio", "screen": "portfolio"}
    harness.outcomes = a2a_turn(
        stream_status(
            "FAILED",
            [{"text": "No fact backs this claim."}, {"data": {"next": portfolio}}],
        )
    )

    response = await _send(client, "Hi")

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "No fact backs this claim.",
        "next": portfolio,
    }


async def test_a_run_the_harness_failed_without_a_reason_streams_a_plain_one(
    client, harness
):
    harness.outcomes = a2a_turn(stream_status("FAILED"))

    response = await _send(client, "Hi")

    assert sse_events(response)[-1] == {
        "status": "failed",
        "reason": "The assistant hit an error. Send your message again.",
        "next": None,
    }


async def test_answering_a_task_the_harness_lost_streams_its_reason(client, harness):
    reason = "Task task-1 not found"
    harness.outcomes = [{"error": {"code": -32001, "message": reason}}]

    response = await _task(client, "answer", {"input": "The queue one"})

    assert sse_events(response) == [
        {"status": "failed", "reason": reason, "next": None}
    ]


async def test_a_harness_that_stays_down_streams_that_it_stopped_responding(
    client, harness
):
    harness.down = True

    response = await _send(client, "Hi")

    events = sse_events(response)
    assert response.status_code == 200
    assert events[0]["status"] == "reconnecting"
    assert events[-1] == GAVE_UP
    assert "started" not in [e["status"] for e in events]


async def test_a_dropped_stream_shows_reconnecting_then_carries_on_to_the_reply(
    client, harness
):
    harness.outcomes = [
        *a2a_turn(stream_status("WORKING")),
        _task_state("COMPLETED", [{"text": "Back again."}]),
    ]

    response = await _send(client, "Hi")

    events = sse_events(response)
    assert [e["status"] for e in events] == [
        "started",
        "reconnecting",
        "reconnected",
        "completed",
    ]
    assert events[1]["attempt"] == 1
    assert datetime.fromisoformat(events[1]["retry_at"])
    assert events[-1] == {"status": "completed", "reply": "Back again."}
    assert [r["method"] for r in a2a_sent(harness)] == [
        "SendMessage",
        "SubscribeToTask",
        "GetTask",
    ]


async def test_a_harness_that_goes_down_mid_turn_is_given_up_on(client, harness):
    def drop(request: dict) -> list:
        """The stream breaks and the harness is gone for good"""
        harness.down = True
        return [stream_task(), stream_status("WORKING")]

    harness.outcomes = [a2a_accepted(), drop]

    response = await _send(client, "Hi")

    events = sse_events(response)
    assert [e["status"] for e in events][:2] == ["started", "reconnecting"]
    assert events[-1] == GAVE_UP
    assert "completed" not in [e["status"] for e in events]
    page = (
        await client.get(f"{AGENT}/threads/{await thread_of(client)}/messages")
    ).json()
    assert page["messages"][-1]["failure"] == GAVE_UP["reason"]


async def _given_up(client, harness) -> str:
    """Send a message whose stream breaks with the harness gone for good, then bring
    the harness back; the thread"""

    def drop(request: dict) -> list:
        """The stream breaks and the harness is gone"""
        harness.down = True
        return [stream_task(), stream_status("WORKING")]

    harness.outcomes = [a2a_accepted(), drop]
    await _send(client, "Hi")
    harness.down = False
    harness.received.clear()
    return await thread_of(client)


def _task_of(thread: str, state: str, message: dict | None = None) -> dict:
    """What GetTask or CancelTask answers for task-1 on the thread"""
    status = {"state": f"TASK_STATE_{state}"} | (
        {"message": message} if message else {}
    )
    return {"result": {"id": "task-1", "contextId": thread, "status": status}}


async def test_a_reply_given_up_on_that_finished_is_kept_before_the_next_turn(
    client, harness
):
    thread = await _given_up(client, harness)
    reply = {
        "messageId": "reply-late",
        "role": "ROLE_AGENT",
        "parts": [{"text": "Two fit."}],
    }
    harness.outcomes = [
        _task_of(thread, "COMPLETED", reply),
        *a2a_replied("Anything else?", "reply-2"),
    ]

    await _send(client, "Thanks")

    page = (await client.get(f"{AGENT}/threads/{thread}/messages")).json()
    assert [(m["id"], m["text"], m["failure"]) for m in page["messages"][1:]] == [
        ("reply-late", "Two fit.", None),
        (page["messages"][2]["id"], "Thanks", None),
        ("reply-2", "Anything else?", None),
    ]
    assert [r["method"] for r in a2a_sent(harness)][:2] == ["GetTask", "SendMessage"]


async def test_a_reply_given_up_on_that_still_runs_is_stopped_before_the_next_turn(
    client, harness
):
    thread = await _given_up(client, harness)
    harness.outcomes = [
        _task_of(thread, "WORKING"),
        _task_of(thread, "WORKING"),
        _task_of(thread, "CANCELED"),
        _task_of(thread, "CANCELED"),
        *a2a_replied("Hello.", "reply-2"),
    ]

    response = await _send(client, "Hi again")

    assert sse_events(response)[-1] == {"status": "completed", "reply": "Hello."}
    assert [r["method"] for r in a2a_sent(harness)][:5] == [
        "GetTask",
        "GetTask",
        "CancelTask",
        "GetTask",
        "SendMessage",
    ]
    page = (await client.get(f"{AGENT}/threads/{thread}/messages")).json()
    assert page["messages"][1]["failure"] == GAVE_UP["reason"]


async def test_a_reply_given_up_on_before_its_task_was_known_is_found_and_stopped(
    client, harness
):
    harness.down = True
    await _send(client, "Hi")
    harness.down = False
    harness.received.clear()
    thread = await thread_of(client)
    harness.outcomes = [
        {"result": {"tasks": [_task_of(thread, "WORKING")["result"]]}},
        _task_of(thread, "WORKING"),
        _task_of(thread, "CANCELED"),
        _task_of(thread, "CANCELED"),
        *a2a_replied("Hello.", "reply-2"),
    ]

    response = await _send(client, "Hi again")

    assert sse_events(response)[-1] == {"status": "completed", "reply": "Hello."}
    assert [r["method"] for r in a2a_sent(harness)][:5] == [
        "ListTasks",
        "GetTask",
        "CancelTask",
        "GetTask",
        "SendMessage",
    ]


async def test_a_reply_given_up_on_that_will_not_stop_holds_the_next_turn(
    client, harness
):
    thread = await _given_up(client, harness)
    harness.outcomes = [_task_of(thread, "WORKING")] * 1000

    response = await _send(client, "Hi again")

    assert response.status_code == 409
    assert "SendMessage" not in [r["method"] for r in a2a_sent(harness)]


async def test_a_reply_is_kept_as_the_agents_message_under_the_harnesss_id(
    client, harness
):
    harness.outcomes = a2a_replied("Two fit.", "reply-9")

    await _send(client, "Find me jobs")

    page = (
        await client.get(f"{AGENT}/threads/{await thread_of(client)}/messages")
    ).json()
    assert [(m["role"], m["text"]) for m in page["messages"]] == [
        ("user", "Find me jobs"),
        ("agent", "Two fit."),
    ]
    assert page["messages"][1]["id"] == "reply-9"
    assert page["messages"][1]["agent"] == "career-director"


async def test_stop_cancels_the_threads_running_task(client, harness):
    thread_id = await thread_of(client)
    task = {
        "id": "task-1",
        "contextId": thread_id,
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}, {"result": task}]

    response = await client.delete(f"{AGENT}/threads/{thread_id}/tasks/task-1")

    assert response.status_code == 204
    assert [(s["method"], s["params"]) for s in a2a_sent(harness)] == [
        ("GetTask", {"id": "task-1"}),
        ("CancelTask", {"id": "task-1"}),
    ]


async def test_stop_leaves_another_threads_task_alone(client, harness):
    task = {
        "id": "task-1",
        "contextId": str(uuid4()),
        "status": {"state": "TASK_STATE_WORKING"},
    }
    harness.outcomes = [{"result": task}]

    response = await client.delete(
        f"{AGENT}/threads/{await thread_of(client)}/tasks/task-1"
    )

    assert response.status_code == 404
    assert [s["method"] for s in a2a_sent(harness)] == ["GetTask"]


async def test_a_stream_closed_before_the_turn_ends_leaves_its_task_running(
    client, harness
):
    harness.outcomes = a2a_turn(
        stream_chunk("text-1", "text", {"text": "Two "}), _completed("Two fit.")
    )
    thread_id = await thread_of(client)

    async with client.stream(
        "POST", f"{AGENT}/threads/{thread_id}/messages", json={"text": "Hi"}
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                break
    replayed = await client.get(f"{AGENT}/threads/{thread_id}/stream")

    assert [e["status"] for e in sse_events(replayed)] == [
        "started",
        "text",
        "completed",
    ]
    assert "CancelTask" not in [s["method"] for s in a2a_sent(harness)]


async def test_a_turn_sends_event_ids_and_a_retry_hint(client, harness):
    harness.outcomes = a2a_replied("Hi.")

    response = await _send(client, "Hi")

    run_id = sse_ids(response)[0].partition(":")[0]
    assert sse_ids(response) == [f"{run_id}:1", f"{run_id}:2"]
    assert "retry: 2000" in response.text.splitlines()


async def test_a_broken_stream_resumes_after_the_last_event_it_got(client, harness):
    harness.outcomes = a2a_turn(
        stream_chunk("text-1", "text", {"text": "Two "}),
        stream_chunk("text-1", "text", {"text": "fit."}),
        _completed("Two fit."),
    )
    thread_id = await thread_of(client)
    first = await _send(client, "Hi")
    second_id = sse_ids(first)[1]

    resumed = await client.get(
        f"{AGENT}/threads/{thread_id}/stream", headers={"Last-Event-ID": second_id}
    )
    replayed = await client.get(f"{AGENT}/threads/{thread_id}/stream")

    assert sse_events(resumed) == sse_events(first)[2:]
    assert sse_ids(resumed) == sse_ids(first)[2:]
    assert sse_events(replayed) == sse_events(first)


async def test_nothing_resumes_from_another_run_or_an_idle_thread(client, harness):
    harness.outcomes = a2a_replied("Hi.")
    thread_id = await thread_of(client)
    await _send(client, "Hi")
    idle = (await client.post(f"{AGENT}/sessions/career-director/threads")).json()

    foreign = await client.get(
        f"{AGENT}/threads/{thread_id}/stream",
        headers={"Last-Event-ID": "0123456789abcdef:1"},
    )
    quiet = await client.get(f"{AGENT}/threads/{idle['thread_id']}/stream")
    theirs = await client.get(f"{AGENT}/threads/{uuid4()}/stream")

    assert foreign.status_code == 404
    assert quiet.status_code == 404
    assert theirs.status_code == 404


async def test_a_thread_takes_no_new_message_while_its_turn_runs(app, client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()
    thread_id = await thread_of(client)
    await app.state.container.store().create(
        UUID(me["id"]), thread_id, "career-director"
    )

    response = await _send(client, "Again")

    assert response.status_code == 409
    assert harness.received == []


async def test_a_turn_executes_the_tools_it_pauses_with(client, harness):
    document = (
        await client.post(
            f"{PREFIX}/documents",
            json={"title": "Résumé for Northwind", "body": RESUME},
        )
    ).json()
    thread_id = await thread_of(client)
    harness.outcomes = tool_pause(
        {"execute_tool": "documents", "name": "northwind"}, "Found it."
    )

    response = await _send(client, "Find my résumé")

    assert [e["status"] for e in sse_events(response)] == ["started", "completed"]
    resume = sent_messages(harness)[1]["message"]
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == thread_id
    [part] = resume["parts"]
    assert part["metadata"] == {"interrupt_id": "interrupt-1"}
    assert [d["id"] for d in part["data"]["documents"]] == [document["id"]]


async def test_a_tool_ops_does_not_have_is_refused_with_why(client, harness):
    harness.outcomes = tool_pause({"execute_tool": "weather"}, "I can't check.")

    response = await _send(client, "Is it sunny?")

    assert sse_events(response)[-1] == {
        "status": "completed",
        "reply": "I can't check.",
    }
    [part] = sent_messages(harness)[1]["message"]["parts"]
    assert part == interrupt_part({"error": "Ops has no weather tool"})


async def test_a_blocking_run_answers_every_tool_its_pause_asks_for(harness):
    async def answer(
        task_id: str, interrupt_id: str, request: ToolRequest
    ) -> _Documents:
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
                        "parts": [
                            interrupt_part(
                                {"execute_tool": "documents", "name": "nw"}, "i-sg"
                            ),
                            interrupt_part(
                                {"execute_tool": "documents", "name": "acme"}, "i-my"
                            ),
                        ],
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
        execute_tool=answer,
    )

    assert run == Completed(reply="ok")
    assert a2a_sent(harness)[1]["params"]["message"]["parts"] == [
        interrupt_part({"documents": ["nw"]}, "i-sg"),
        interrupt_part({"documents": ["acme"]}, "i-my"),
    ]


async def test_a_turn_keeps_each_model_calls_usage_as_its_user_and_never_streams_it(
    app, client, harness
):
    me = (await client.get(f"{PREFIX}/me")).json()
    thread_id = await thread_of(client)
    harness.outcomes = a2a_turn(
        stream_status("WORKING", [{"data": {"usage": USAGE}}]), _completed("Hi.")
    )

    response = await _send(client, "Hi")

    assert [e["status"] for e in sse_events(response)] == ["started", "completed"]
    async with app.state.container.session_factory()() as session:
        [call] = (await session.scalars(select(AgentModelCall))).all()
    assert (call.user_id, call.thread_id, call.task_id) == (
        UUID(me["id"]),
        thread_id,
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

    async def answer(
        task_id: str, interrupt_id: str, request: ToolRequest
    ) -> _Documents:
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
        "parts": [interrupt_part({"execute_tool": "documents"})],
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
        execute_tool=answer,
    )

    assert run == Completed(reply="ok")
    assert kept == [("u:c", "task-1", "first"), ("u:c", "task-1", "second")]


def _proposing(harness: FakeHarness, document_id: str) -> list:
    """The harness's turn proposing TAILOR for the document: the propose_changeset
    request, then a changeset artifact naming the changeset ops-api answered with"""

    def published(request: dict) -> list:
        """The rest of the turn, built from the changeset ops-api just stored"""
        [part] = sent_messages(harness)[-1]["message"]["parts"]
        return [
            stream_task(),
            stream_chunk(
                "changeset-1",
                "changeset",
                {
                    "data": {
                        "document_id": document_id,
                        "changeset_id": part["data"]["changeset_id"],
                    }
                },
            ),
            _completed("Review my edits."),
        ]

    return [
        *a2a_turn(
            _paused(
                {
                    "execute_tool": "propose_changeset",
                    "document_id": document_id,
                    "changeset": TAILOR,
                }
            )
        ),
        a2a_accepted(),
        published,
    ]


async def test_edits_career_director_proposes_are_stored_and_announced(client, harness):
    document = (
        await client.post(
            f"{PREFIX}/documents", json={"title": "Master résumé", "body": RESUME}
        )
    ).json()
    harness.outcomes = _proposing(harness, document["id"])

    response = await _send(client, "Tailor it")

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
            "changeset_id": stored["id"],
            "created_at": stored["created_at"],
        },
        {"status": "completed", "reply": "Review my edits."},
    ]
    [answer] = sent_messages(harness)[1]["message"]["parts"]
    assert answer["data"] == {"changeset_id": stored["id"]}


async def test_every_changeset_a_turn_proposes_is_kept_on_its_message(client, harness):
    proposed = []
    for title in ["Backend résumé", "Frontend résumé"]:
        document = (
            await client.post(
                f"{PREFIX}/documents", json={"title": title, "body": RESUME}
            )
        ).json()
        await client.post(
            f"{PREFIX}/documents/{document['id']}/changesets", json=TAILOR
        )
        [changeset] = (
            await client.get(f"{PREFIX}/documents/{document['id']}/changesets")
        ).json()
        proposed.append(
            {
                "id": changeset["id"],
                "document_id": document["id"],
                "created_at": changeset["created_at"],
            }
        )
    harness.outcomes = a2a_turn(
        *(
            stream_chunk(
                f"changeset-{index}",
                "changeset",
                {"data": {"document_id": p["document_id"], "changeset_id": p["id"]}},
            )
            for index, p in enumerate(reversed(proposed))
        ),
        _completed("Review my edits."),
    )

    response = await _send(client, "Tailor both")

    assert [
        (e["changeset_id"], e["created_at"])
        for e in sse_events(response)
        if e["status"] == "changeset"
    ] == [(p["id"], p["created_at"]) for p in reversed(proposed)]
    page = (
        await client.get(f"{AGENT}/threads/{await thread_of(client)}/messages")
    ).json()
    assert page["messages"][-1]["changesets"] == proposed


async def test_a_changeset_published_again_after_a_takeover_is_announced_once(
    client, harness
):
    document = (
        await client.post(
            f"{PREFIX}/documents", json={"title": "Master résumé", "body": RESUME}
        )
    ).json()
    changeset = (
        await client.post(
            f"{PREFIX}/documents/{document['id']}/changesets", json=TAILOR
        )
    ).json()
    published = stream_chunk(
        "changeset-1",
        "changeset",
        {"data": {"document_id": document["id"], "changeset_id": changeset["id"]}},
    )
    harness.outcomes = [
        *a2a_turn(published, stream_status("WORKING")),
        {"result": a2a_task("WORKING")["result"]["task"]},
        [stream_task(), published, _completed("Review my edits.")],
    ]

    response = await _send(client, "Tailor it")

    assert [e["status"] for e in sse_events(response)] == [
        "started",
        "changeset",
        "reconnecting",
        "reconnected",
        "completed",
    ]


async def test_a_changeset_artifact_naming_nothing_of_the_users_is_skipped(
    app, client, harness
):
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
    harness.outcomes = a2a_turn(
        stream_chunk(
            "changeset-1",
            "changeset",
            {"data": {"document_id": str(theirs.id), "changeset_id": str(uuid4())}},
        ),
        _completed("Review my edits."),
    )

    response = await _send(client, "Tailor it")

    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "completed", "reply": "Review my edits."},
    ]
    async with app.state.session_factory() as session:
        assert (await session.scalars(select(DocumentChangeset))).all() == []


async def test_edits_to_another_users_document_are_refused_back_to_the_agent(
    app, client, harness
):
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
    harness.outcomes = tool_pause(
        {
            "execute_tool": "propose_changeset",
            "document_id": str(theirs.id),
            "changeset": TAILOR,
        },
        "I could not reach it.",
    )

    await _send(client, "Tailor it")

    [part] = sent_messages(harness)[1]["message"]["parts"]
    assert set(part["data"]) == {"error"}
    async with app.state.session_factory() as session:
        assert (await session.scalars(select(DocumentChangeset))).all() == []


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


def _review(*args: dict) -> dict:
    """The status pausing a turn for the user to approve update_profile calls"""
    return stream_status(
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
    )


def _decisions(harness) -> list[dict]:
    """The decisions ops-api sent on its last message to the harness"""
    [part] = sent_messages(harness)[-1]["message"]["parts"]
    return part["data"]["decisions"]


async def test_a_message_sent_while_changes_wait_rejects_them_with_it(client, harness):
    await _seed(client)
    edit = {"kind": "about", "field": "headline", "value": "Staff Engineer"}
    harness.outcomes = [
        *a2a_turn(_review({"edits": [edit]})),
        *a2a_replied("Made it Principal Engineer instead."),
    ]

    await _send(client, "Change my headline")
    await _send(client, "Make it Principal Engineer")

    assert _decisions(harness) == [
        {"type": "reject", "message": "Make it Principal Engineer"}
    ]
    assert sent_messages(harness)[-1]["message"]["taskId"] == "task-1"


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
    harness.outcomes = a2a_turn(_review({"edits": edits, "source": "Backend résumé"}))
    stored = await _stored(client)

    response = await _send(client, "Sync me")

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
        *a2a_turn(_review({"edits": edits})),
        *a2a_turn(_paused({"execute_tool": "profile_update", "edits": edits})),
        *a2a_turn(
            stream_chunk("p-1", "profile_updated", {"data": {"saved": 5}}),
            _completed("Saved."),
        ),
    ]
    await _send(client, "Update me")

    response = await _task(client, "decision", {"approve": True})

    assert sse_events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "profile_saved", "saved": 5},
        {"status": "completed", "reply": "Saved."},
    ]
    sent = sent_messages(harness)
    assert sent[1]["message"]["taskId"] == "task-1"
    assert sent[1]["message"]["parts"] == [
        {"data": {"decisions": [{"type": "approve"}]}}
    ]
    assert sent[2]["message"]["parts"] == [interrupt_part({"saved": 5})]
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
        *a2a_turn(_review({"edits": [edit]})),
        *a2a_replied("Kept it."),
        *a2a_turn(_review({"edits": [edit]})),
        *a2a_replied("Left it.", "reply-2"),
    ]
    stored = await _stored(client)

    await _send(client, "Change my headline")
    with_reason = await _task(
        client, "decision", {"approve": False, "message": "Keep my headline"}
    )
    sent_with_reason = _decisions(harness)
    await _send(client, "Change my headline")
    await _task(client, "decision", {"approve": False})

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

    def entry(field: str, value: object, fact: str = fact) -> dict:
        """An edit to one field of an entry"""
        return {"kind": "entry", "fact": fact, "field": field, "value": value}

    cases = [
        ([{"edits": [{"kind": "about", "field": "nickname", "value": "K"}]}], "field"),
        ([{"edits": [edit], "current": "Engineer"}], "current"),
        ([{"edits": [entry("title", "X", unknown)]}], unknown),
        ([{"edits": [entry("end", "2019-01")]}], "end must not be before start"),
        ([{"edits": [entry("tools", ["Go"])]}], "Only a project"),
        (
            [{"edits": [{"kind": "new_skill", "name": " python "}]}],
            "Python is already a skill",
        ),
        ([{"edits": [edit]}, {"edits": [edit]}], "one update_profile call"),
    ]
    stored = await _stored(client)

    for actions, reason in cases:
        harness.outcomes = [
            *a2a_turn(_review(*actions)),
            *a2a_replied("Let me fix that."),
        ]

        response = await _send(client, "Update me")

        assert [e["status"] for e in sse_events(response)] == [
            "started",
            "started",
            "completed",
        ]
        decisions = _decisions(harness)
        assert [d["type"] for d in decisions] == ["reject"] * len(actions)
        assert all(reason in d["message"] for d in decisions)
    assert await _stored(client) == stored


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
    harness.outcomes = tool_pause(
        {"execute_tool": "profile_sync", "document_id": document["id"]},
        "Four changes.",
    )
    stored = await _stored(client)

    await _send(client, "Sync with my résumé")

    [part] = sent_messages(harness)[1]["message"]["parts"]
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


async def test_a_job_run_the_director_asks_for_is_queued_and_answered(client, harness):
    search = {"query": "Staff engineer", "location": None, "posted_within": None}
    harness.outcomes = [
        *tool_pause(
            {
                "execute_tool": "job_run",
                "run_after": "2026-11-13T08:00:00+08:00",
                "search": search,
            },
            "Queued for tomorrow at 8.",
        ),
        *a2a_turn(
            _paused(
                {"execute_tool": "job_run", "run_after": None, "search": None},
                "interrupt-2",
            )
        ),
        *a2a_replied("One is already queued.", "reply-2"),
    ]

    await _send(client, "Search tomorrow at 8")
    await _send(client, "Search now")

    run = (await client.get(f"{PREFIX}/jobs/runs/latest")).json()
    assert (run["trigger"], run["status"]) == ("agent", "queued")
    assert run["run_after"].startswith("2026-11-13T")
    sent = sent_messages(harness)
    [answer] = sent[1]["message"]["parts"]
    assert answer["data"]["id"] == run["id"]
    assert datetime.fromisoformat(
        answer["data"]["run_after"]
    ) == datetime.fromisoformat("2026-11-13T08:00:00+08:00")
    assert sent[3]["message"]["parts"] == [
        interrupt_part({"error": "A job agent run is already queued"}, "interrupt-2")
    ]


def _delegating(director: str, request: dict, answers: list, repeats: int = 1):
    """The harness pausing career-director's turn on its thread on request, repeats
    times under one interrupt, then replying, and replying at once on every other
    thread; answers collects each tool answer it is sent"""
    left = [repeats]

    def respond(sent: dict) -> dict | list:
        """Take a message as a task named after its thread, or stream that task"""
        if sent["method"] == "SendMessage":
            message = sent["params"]["message"]
            if message.get("taskId"):
                answers.append(message["parts"])
            return a2a_accepted(message["contextId"])
        task = sent["params"]["id"]
        if task == director and left[0]:
            left[0] -= 1
            return [stream_task(), _paused(request)]
        return [
            stream_task(),
            stream_status("COMPLETED", [{"text": "Done."}], uuid4().hex),
        ]

    return respond


def _started(harness: FakeHarness) -> dict[str, str]:
    """The document each new career-consultant message was about, by its thread"""
    return {
        m["message"]["contextId"]: m["message"]["parts"][1]["data"]["document_id"]
        for m in sent_messages(harness)
        if not m["message"].get("taskId")
        and "document" in m["message"]["parts"][1]["data"]
    }


async def _ended(client, document_id: str) -> dict:
    """How the document's career-consultant thread's turn ended"""
    thread = await thread_of(client, "career-consultant", document_id)
    return sse_events(await client.get(f"{AGENT}/threads/{thread}/stream"))[-1]


async def test_a_write_asked_for_again_under_the_same_interrupt_runs_once(
    client, harness
):
    queue = {"execute_tool": "job_run", "run_after": None, "search": None}
    harness.outcomes = [
        *a2a_turn(_paused(queue)),
        *a2a_turn(_paused(queue)),
        *a2a_replied("Queued."),
    ]

    response = await _send(client, "Search now")

    assert sse_events(response)[-1] == {"status": "completed", "reply": "Queued."}
    first, second = (m["message"]["parts"] for m in sent_messages(harness)[1:])
    assert "error" not in first[0]["data"]
    assert second == first


async def test_only_a_resume_or_cv_has_a_sync_preview(client, harness):
    letter = (
        await client.post(
            f"{PREFIX}/documents", json={"title": "Letter", "body": LETTER}
        )
    ).json()
    harness.outcomes = []
    for document_id in (letter["id"], str(uuid4())):
        harness.outcomes += tool_pause(
            {"execute_tool": "profile_sync", "document_id": document_id},
            "That isn't a résumé.",
        )

    await _send(client, "Sync with my letter")
    await _send(client, "Sync with that one")

    sent = sent_messages(harness)
    assert [s["message"]["parts"] for s in (sent[1], sent[3])] == [
        [interrupt_part({"error": "No such résumé or CV"})]
    ] * 2


async def test_an_update_saves_all_its_changes_or_none(client, harness):
    await _seed(client)
    edits = [
        {"kind": "about", "field": "headline", "value": "Staff Engineer"},
        {"kind": "new_skill", "name": "Go"},
        {"kind": "entry", "fact": f"role-{uuid4()}", "field": "title", "value": "X"},
    ]
    harness.outcomes = tool_pause(
        {"execute_tool": "profile_update", "edits": edits}, "Nothing was saved."
    )
    stored = await _stored(client)

    await _send(client, "Update me")

    [part] = sent_messages(harness)[1]["message"]["parts"]
    assert part == interrupt_part({"error": f"No such entry {edits[2]['fact']}"})
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
        harness.outcomes = tool_pause(
            {"execute_tool": "profile_update", "edits": [headline, edit]},
            "Nothing was saved.",
        )

        await _send(client, "Update me")

        [part] = sent_messages(harness)[-1]["message"]["parts"]
        assert part == interrupt_part(
            {
                "error": "Only a project has a link, code link, tools or a place"
                " on the site"
            }
        )
    assert await _stored(client) == stored
