from __future__ import annotations

from typing import NamedTuple

from pydantic import TypeAdapter

from src.clients.ezcareer.a2a import Artifact, StatusMessage, TaskStatus, UsageData
from src.clients.ezcareer.schemas import (
    Action,
    Cancelled,
    Completed,
    Failed,
    InputRequired,
    NextScreen,
    Replied,
    ReviewRequired,
    RunEvent,
    ToolRequest,
    ToolsRequested,
    Usage,
    Widget,
)


class TaskState(NamedTuple):
    task_id: str
    """The task"""

    events: list[RunEvent[str] | ToolsRequested]
    """What its status says: nothing while it works, the tools it asks for, or the
    message ending the turn and how it ended"""


def tool_requests(status: TaskStatus) -> list[tuple[str, ToolRequest]]:
    """Each tool a paused task asks ops-api to execute, under its interrupt id; empty
    when the task waits for anything else"""
    parts = status.message.parts if status.message else []
    requests = [
        (str(part.metadata["interrupt_id"]), ToolRequest.model_validate(part.data))
        for part in parts
        if isinstance(part.data, dict)
        and "execute_tool" in part.data
        and part.metadata
        and "interrupt_id" in part.metadata
    ]
    return requests if len(requests) == len(parts) else []


def review_required(task_id: str, status: TaskStatus) -> ReviewRequired | None:
    """The tool calls a paused task waits for the user to approve, or None when it
    asks something else"""
    data = status.message.parts[0].data if status.message else None
    return (
        ReviewRequired(
            task_id=task_id,
            actions=TypeAdapter(list[Action]).validate_python(data["action_requests"]),
        )
        if isinstance(data, dict) and "action_requests" in data
        else None
    )


def call_usage(message: StatusMessage | None) -> Usage | None:
    """The model call's usage a status message carries, if it carries one"""
    data = message.parts[0].data if message else None
    return (
        UsageData.model_validate(data).usage
        if isinstance(data, dict) and "usage" in data
        else None
    )


def failure(status: TaskStatus) -> Failed:
    """Why a task stopped, as the harness put it or in plain words when it gave no
    reason, with the screen a data part names"""
    parts = status.message.parts if status.message else []
    screen = next(
        (
            p.data["next"]
            for p in parts
            if isinstance(p.data, dict) and p.data.get("next")
        ),
        None,
    )
    return Failed(
        reason=" ".join(part.text for part in parts if part.text)
        or "The assistant hit an error. Send your message again.",
        next=NextScreen.model_validate(screen) if screen else None,
    )


def reply_text(executable: str, artifacts: list[Artifact]) -> str | None:
    """The text of the executable's reply artifact, if the task has one yet"""
    return next(
        (
            "".join(part.text or "" for part in artifact.parts)
            for artifact in artifacts
            if artifact.name == executable
        ),
        None,
    )


def status_events(
    task_id: str, status: TaskStatus, reply: str | None
) -> list[RunEvent[str] | ToolsRequested]:
    """What a task's status says about its run: nothing while it works, the tools it
    asks ops-api to execute, or the message ending the turn and how it ended"""
    message = status.message
    match status.state:
        case "TASK_STATE_SUBMITTED" | "TASK_STATE_WORKING":
            return []
        case "TASK_STATE_INPUT_REQUIRED" if requests := tool_requests(status):
            return [ToolsRequested(task_id=task_id, requests=requests)]
        case "TASK_STATE_INPUT_REQUIRED" if review := review_required(task_id, status):
            ended: RunEvent[str] = review
        case "TASK_STATE_INPUT_REQUIRED" if message:
            ended = InputRequired(
                task_id=task_id, widget=Widget.model_validate(message.parts[0].data)
            )
        case "TASK_STATE_COMPLETED":
            text = (
                "".join(part.text for part in message.parts if part.text)
                if message
                else ""
            )
            ended = Completed(reply=text or reply or "")
        case "TASK_STATE_CANCELED":
            ended = Cancelled()
        case _:
            ended = failure(status)
    replied = (
        [Replied(message_id=message.message_id)]
        if message and message.message_id
        else []
    )
    return [*replied, ended]


__all__ = [
    "TaskState",
    "call_usage",
    "failure",
    "reply_text",
    "review_required",
    "status_events",
    "tool_requests",
]
