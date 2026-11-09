import json

from tests.conftest import PREFIX

ASSISTANT = f"{PREFIX}/assistant"

WIDGET = {
    "label": "May I go ahead? Save the job to your list.",
    "submit_btn": "Confirm",
    "cancel_btn": "Cancel",
}


def _task(state: str, *, status_parts=None, artifact_parts=None) -> dict:
    """A SendMessage result as the harness's A2A 1.0 server returns it"""
    task = {
        "id": "task-1",
        "contextId": "context-1",
        "status": {"state": f"TASK_STATE_{state}"},
    }
    if status_parts is not None:
        task["status"]["message"] = {
            "messageId": "m-agent",
            "role": "ROLE_AGENT",
            "parts": status_parts,
        }
    if artifact_parts is not None:
        task["artifacts"] = [
            {"artifactId": "a-1", "name": "career-director", "parts": artifact_parts}
        ]
    return {"result": {"task": task}}


def _sent(harness) -> list[dict]:
    """The A2A requests the harness received, as JSON"""
    return [json.loads(request.content) for request in harness.received]


async def test_a_message_reaches_career_director_with_the_profile(client, harness):
    await client.patch(
        f"{PREFIX}/profile", json={"preferences": {"work_modes": ["remote"]}}
    )
    await client.post(
        f"{PREFIX}/profile/skills", json={"name": "Python", "group": "Languages"}
    )
    agent_profile = (await client.get(f"{PREFIX}/profile/agent")).json()
    me = (await client.get(f"{PREFIX}/me")).json()
    harness.outcomes = [_task("COMPLETED", artifact_parts=[{"text": "Two fit."}])]

    response = await client.post(
        f"{ASSISTANT}/messages", json={"text": "Find me remote jobs"}
    )

    assert response.status_code == 200
    assert response.json() == {"status": "completed", "reply": "Two fit."}
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/career-director"
    assert request.headers["A2A-Version"] == "1.0"
    [sent] = _sent(harness)
    assert sent["method"] == "SendMessage"
    message = sent["params"]["message"]
    assert message["role"] == "ROLE_USER"
    assert message["contextId"] == me["id"]
    assert "taskId" not in message
    assert message["parts"] == [
        {"text": "Find me remote jobs"},
        {"data": agent_profile},
    ]


async def test_a_widget_is_shown_and_the_answer_resumes_its_task(client, harness):
    harness.outcomes = [
        _task("INPUT_REQUIRED", status_parts=[{"data": WIDGET}]),
        _task("COMPLETED", artifact_parts=[{"text": "Saved it."}]),
    ]

    asked = await client.post(f"{ASSISTANT}/messages", json={"text": "Save it"})
    done = await client.post(f"{ASSISTANT}/tasks/task-1/answer", json={"accept": True})

    assert asked.json() == {
        "status": "input_required",
        "task_id": "task-1",
        "widget": {
            "label": WIDGET["label"],
            "input_value": None,
            "input_placeholder": None,
            "submit_btn": "Confirm",
            "cancel_btn": "Cancel",
        },
    }
    assert done.json() == {"status": "completed", "reply": "Saved it."}
    first, resume = (sent["params"]["message"] for sent in _sent(harness))
    assert resume["taskId"] == "task-1"
    assert resume["contextId"] == first["contextId"]
    assert resume["parts"] == [{"data": {"input": None, "accept": True}}]


async def test_a_failed_task_returns_its_reason(client, harness):
    harness.outcomes = [
        _task("FAILED", status_parts=[{"text": "Ran out of steps before finishing"}])
    ]

    response = await client.post(f"{ASSISTANT}/messages", json={"text": "Hi"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "failed",
        "reason": "Ran out of steps before finishing",
    }


async def test_answering_a_task_the_harness_lost_fails_with_its_reason(client, harness):
    reason = "Task task-1 not found"
    harness.outcomes = [{"error": {"code": -32001, "message": reason}}]

    response = await client.post(
        f"{ASSISTANT}/tasks/task-1/answer", json={"input": "The queue one"}
    )

    assert response.json() == {"status": "failed", "reason": reason}


async def test_unreachable_harness_gives_a_clear_error(client, harness):
    harness.down = True

    response = await client.post(f"{ASSISTANT}/messages", json={"text": "Hi"})

    assert response.status_code == 503
    assert response.json() == {
        "detail": "ezcareer-harness did not answer career-director; try again later"
    }


async def test_a_reply_ops_api_cannot_read_gives_the_same_error(client, harness):
    harness.outcomes = [_task("COMPLETED", artifact_parts=[])]

    response = await client.post(f"{ASSISTANT}/messages", json={"text": "Hi"})

    assert response.status_code == 503
