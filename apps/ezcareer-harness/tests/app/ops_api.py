import json
from collections.abc import Mapping
from itertools import count

from fastapi.testclient import TestClient
from pydantic import JsonValue

SENT_AT = "2026-11-20T09:30:00Z"
_ids = count()


def _params(
    parts: list[dict[str, JsonValue]],
    task: Mapping[str, JsonValue] | None,
    context: str | None,
    metadata: dict[str, JsonValue] | None,
) -> dict[str, JsonValue]:
    """SendMessage params for one message, on the task or context when given; one
    that starts a task carries when the user sent it, as ops-api's do"""
    message = {"messageId": f"m-{next(_ids)}", "role": "ROLE_USER", "parts": parts}
    if task:
        message |= {"taskId": task["id"], "contextId": task["contextId"]}
    else:
        message |= {"metadata": {"created_at": SENT_AT, "timezone": "Europe/London"}}
    if context:
        message |= {"contextId": context}
    return {"message": message, "metadata": metadata or {}}


def _answers(
    task: Mapping[str, JsonValue], answers: Mapping[str, JsonValue]
) -> list[dict[str, JsonValue]] | None:
    """One answer part per execute_tool request the task paused with, or None when
    it paused for something answers doesn't hold or holds as None"""
    status = task["status"]
    if status["state"] != "TASK_STATE_INPUT_REQUIRED":
        return None
    parts = status["message"]["parts"]
    tools = [
        part["data"].get("execute_tool") if isinstance(part["data"], dict) else None
        for part in parts
    ]
    if not all(answers.get(tool) is not None for tool in tools):
        return None
    return [
        {"data": answers[tool], "metadata": part["metadata"]}
        for tool, part in zip(tools, parts, strict=True)
    ]


def send(
    client: TestClient,
    path: str,
    parts: list[dict[str, JsonValue]],
    *,
    task: Mapping[str, JsonValue] | None = None,
    context: str | None = None,
    answers: Mapping[str, JsonValue] | None = None,
    metadata: dict[str, JsonValue] | None = None,
    asked: list[JsonValue] | None = None,
) -> dict[str, JsonValue]:
    """Sends a message as ops-api does and answers each execute_tool request answers
    holds, adding each one it answers to asked"""
    answers = answers or {}
    params = _params(parts, task, context, metadata)
    while True:
        result = client.post(
            path,
            headers={"A2A-Version": "1.0"},
            json={"jsonrpc": "2.0", "id": 1, "method": "SendMessage", "params": params},
        ).json()["result"]["task"]
        answered = _answers(result, answers)
        if answered is None:
            return result
        if asked is not None:
            asked += [p["data"] for p in result["status"]["message"]["parts"]]
        params = _params(answered, result, None, metadata)


def stream(
    client: TestClient,
    path: str,
    parts: list[dict[str, JsonValue]],
    *,
    task: Mapping[str, JsonValue] | None = None,
    answers: Mapping[str, JsonValue] | None = None,
) -> list[dict[str, JsonValue]]:
    """Every event SendStreamingMessage sends for a message and for the answers to the
    execute_tool requests whose tool answers holds"""
    answers = answers or {}
    params = _params(parts, task, None, None)
    events: list[dict[str, JsonValue]] = []
    while True:
        with client.stream(
            "POST",
            path,
            headers={"A2A-Version": "1.0"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "SendStreamingMessage",
                "params": params,
            },
        ) as response:
            events += [
                json.loads(line.removeprefix("data: "))["result"]
                for line in response.iter_lines()
                if line.startswith("data: ")
            ]
        last = events[-1]["statusUpdate"]
        answered = _answers(last, answers)
        if answered is None:
            return events
        params = _params(
            answered,
            {"id": last["taskId"], "contextId": last["contextId"]},
            None,
            None,
        )
