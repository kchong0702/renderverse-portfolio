import json
from uuid import UUID

import httpx2
from pydantic import BaseModel

from src.clients.ezcareer import Answer, EzcareerClient
from src.clients.ezcareer.schemas import Completed, DataRequest, Started
from src.core.config import get_settings
from tests.conftest import PREFIX

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


def _task() -> dict:
    """The task SendStreamingMessage sends first"""
    return {
        "result": {
            "task": {
                "id": "task-1",
                "contextId": "context-1",
                "status": {"state": "TASK_STATE_SUBMITTED"},
            }
        }
    }


def _status(state: str, parts: list[dict] | None = None) -> dict:
    """A status update of task-1, with a message when parts are given"""
    status: dict = {"state": f"TASK_STATE_{state}"}
    if parts is not None:
        status["message"] = {"messageId": "m", "role": "ROLE_AGENT", "parts": parts}
    return {
        "result": {
            "statusUpdate": {
                "taskId": "task-1",
                "contextId": "context-1",
                "status": status,
            }
        }
    }


def _chunk(artifact_id: str, name: str, part: dict) -> dict:
    """An artifact update of task-1"""
    return {
        "result": {
            "artifactUpdate": {
                "taskId": "task-1",
                "contextId": "context-1",
                "artifact": {"artifactId": artifact_id, "name": name, "parts": [part]},
            }
        }
    }


def _replied(text: str) -> list[dict]:
    """A turn that only replies with text"""
    return [
        _task(),
        _chunk("a-1", "career-director", {"text": text}),
        _status("COMPLETED"),
    ]


def _events(response) -> list[dict]:
    """The run events an SSE response carried"""
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def _sent(harness) -> list[dict]:
    """The A2A requests the harness received, as JSON"""
    return [json.loads(request.content) for request in harness.received]


async def test_a_message_streams_career_directors_turn_with_the_profile(
    client, harness
):
    await client.patch(
        f"{PREFIX}/profile", json={"preferences": {"work_modes": ["remote"]}}
    )
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [
        [
            _task(),
            _status("WORKING"),
            _status("WORKING", [{"data": {"step": STEP | {"status": "running"}}}]),
            _chunk("thinking-1", "thinking", {"text": "Look for remote roles."}),
            _status("WORKING", [{"data": {"step": STEP | {"status": "done"}}}]),
            _chunk("text-2", "text", {"text": "Two "}),
            _chunk("text-2", "text", {"text": "fit."}),
            _chunk("a-1", "career-director", {"text": "Two fit."}),
            _status("COMPLETED"),
        ]
    ]

    response = await client.post(
        f"{CHAT}/messages", json={"text": "Find me remote jobs"}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert _events(response) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "step", "step": STEP | {"status": "running"}},
        {"status": "thinking", "turn": "thinking-1", "text": "Look for remote roles."},
        {"status": "step", "step": STEP | {"status": "done"}},
        {"status": "text", "turn": "text-2", "text": "Two "},
        {"status": "text", "turn": "text-2", "text": "fit."},
        {"status": "completed", "reply": "Two fit."},
    ]
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/career-director"
    assert request.headers["A2A-Version"] == "1.0"
    assert request.headers["Accept"] == "text/event-stream"
    [sent] = _sent(harness)
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
        [_task(), _status("INPUT_REQUIRED", [{"data": WIDGET}])],
        _replied("Saved it."),
    ]

    await client.post(f"{CHAT}/messages", json={"text": "Save it"})
    await client.post(f"{CHAT}/tasks/task-1/answer", json={"accept": True})

    first, resume = (sent["params"] for sent in _sent(harness))
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

    assert [sent["params"]["message"]["contextId"] for sent in _sent(harness)] == [
        f"{me['id']}:{CHAT_ID}",
        f"{me['id']}:{OTHER_CHAT_ID}",
    ]


async def test_a_widget_is_shown_and_the_answer_streams_the_rest_of_the_turn(
    client, harness
):
    harness.outcomes = [
        [_task(), _status("INPUT_REQUIRED", [{"data": WIDGET}])],
        [
            _status("WORKING"),
            _chunk("a-1", "career-director", {"text": "Saved it."}),
            _status("COMPLETED"),
        ],
    ]

    asked = await client.post(f"{CHAT}/messages", json={"text": "Save it"})
    done = await client.post(f"{CHAT}/tasks/task-1/answer", json={"accept": True})

    assert _events(asked)[-1] == {
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
    assert _events(done) == [
        {"status": "started", "task_id": "task-1"},
        {"status": "completed", "reply": "Saved it."},
    ]
    first, resume = (sent["params"]["message"] for sent in _sent(harness))
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == first["contextId"]
    assert resume["parts"] == [{"data": {"input": None, "accept": True}}]


async def test_a_failed_task_streams_its_reason(client, harness):
    harness.outcomes = [
        [
            _task(),
            _status("FAILED", [{"text": "Ran out of steps before finishing"}]),
        ]
    ]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert _events(response)[-1] == {
        "status": "failed",
        "reason": "Ran out of steps before finishing",
    }


async def test_a_stopped_turn_streams_that_it_was_cancelled(client, harness):
    harness.outcomes = [[_task(), _status("CANCELED")]]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert _events(response)[-1] == {"status": "cancelled"}


async def test_answering_a_task_the_harness_lost_streams_its_reason(client, harness):
    reason = "Task task-1 not found"
    harness.outcomes = [[{"error": {"code": -32001, "message": reason}}]]

    response = await client.post(
        f"{CHAT}/tasks/task-1/answer", json={"input": "The queue one"}
    )

    assert _events(response) == [{"status": "failed", "reason": reason}]


async def test_an_unreachable_harness_streams_a_clear_reason(client, harness):
    harness.down = True

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert response.status_code == 200
    assert _events(response) == [
        {
            "status": "failed",
            "reason": "ezcareer-harness did not answer career-director; try again later",
        }
    ]


async def test_a_reply_ops_api_cannot_read_streams_the_same_reason(client, harness):
    harness.outcomes = [[_task(), _chunk("a-1", "career-director", {"data": 1})]]
    harness.outcomes[0].append(_status("COMPLETED"))

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    assert _events(response)[-1] == {
        "status": "failed",
        "reason": "ezcareer-harness did not answer career-director; try again later",
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
    assert [(s["method"], s["params"]) for s in _sent(harness)] == [
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
    assert [s["method"] for s in _sent(harness)] == ["GetTask"]


async def test_a_stream_closed_before_the_turn_ends_cancels_its_task(harness):
    cancelled = {"id": "task-1", "status": {"state": "TASK_STATE_CANCELED"}}
    harness.outcomes = [[_task(), _status("WORKING")], {"result": cancelled}]
    ezcareer = EzcareerClient(get_settings().ezcareer, httpx2.MockTransport(harness))
    run = ezcareer.stream(
        "career-director",
        str,
        context_id="u:c",
        data=Answer(),
        metadata=None,
    )

    assert await anext(run) == Started(task_id="task-1")
    await run.aclose()

    assert [(s["method"], s["params"].get("id")) for s in _sent(harness)] == [
        ("SendStreamingMessage", None),
        ("CancelTask", "task-1"),
    ]


def _ids(response) -> list[str]:
    """The SSE event ids a response carried"""
    return [
        line.removeprefix("id: ")
        for line in response.text.splitlines()
        if line.startswith("id: ")
    ]


async def test_a_turn_sends_event_ids_and_a_retry_hint(client, harness):
    harness.outcomes = [_replied("Hi.")]

    response = await client.post(f"{CHAT}/messages", json={"text": "Hi"})

    run_id = _ids(response)[0].partition(":")[0]
    assert _ids(response) == [f"{run_id}:1", f"{run_id}:2"]
    assert "retry: 2000" in response.text.splitlines()


async def test_a_broken_stream_resumes_after_the_last_event_it_got(client, harness):
    harness.outcomes = [
        [
            _task(),
            _chunk("text-1", "text", {"text": "Two "}),
            _chunk("text-1", "text", {"text": "fit."}),
            _chunk("a-1", "career-director", {"text": "Two fit."}),
            _status("COMPLETED"),
        ]
    ]
    first = await client.post(f"{CHAT}/messages", json={"text": "Hi"})
    second_id = _ids(first)[1]

    resumed = await client.get(f"{CHAT}/stream", headers={"Last-Event-ID": second_id})
    replayed = await client.get(f"{CHAT}/stream")

    assert _events(resumed) == _events(first)[2:]
    assert _ids(resumed) == _ids(first)[2:]
    assert _events(replayed) == _events(first)


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
            _task(),
            _status("INPUT_REQUIRED", [{"data": {"fetch": "documents", "name": "nw"}}]),
        ],
        [
            _status("WORKING"),
            _chunk("a-1", "career-director", {"text": "Found it."}),
            _status("COMPLETED"),
        ],
    ]
    ezcareer = EzcareerClient(get_settings().ezcareer, httpx2.MockTransport(harness))

    events = [
        event
        async for event in ezcareer.stream(
            "career-director",
            str,
            context_id="u:c",
            data=Answer(),
            metadata=None,
            answer_data_request=answer,
        )
    ]

    assert events == [Started(task_id="task-1"), Completed(reply="Found it.")]
    assert [r.model_dump() for r in asked] == [{"fetch": "documents", "name": "nw"}]
    resume = _sent(harness)[1]["params"]["message"]
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == "u:c"
    assert resume["parts"] == [{"data": {"documents": ["Résumé for Northwind"]}}]


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
    ezcareer = EzcareerClient(get_settings().ezcareer, httpx2.MockTransport(harness))

    run = await ezcareer.send(
        "edit-document",
        str,
        context_id="u:c",
        data=Answer(),
        metadata=None,
        answer_data_request=answer,
    )

    assert run == Completed(reply="ok")
    assert _sent(harness)[1]["params"]["message"]["parts"] == [
        {"data": {"documents": ["nw"]}}
    ]
