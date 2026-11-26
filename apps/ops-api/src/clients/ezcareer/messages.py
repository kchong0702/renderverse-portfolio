from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel

from src.clients.ezcareer.a2a import DataPart, Message, TextPart
from src.clients.ezcareer.schemas import MessageMetadata


def new_message(
    context_id: str,
    message_id: str,
    text: str,
    data: BaseModel,
    metadata: MessageMetadata | None = None,
) -> Message:
    """A message starting a run on the user's text and its input data"""
    return Message(
        message_id=message_id,
        context_id=context_id,
        parts=[TextPart(text=text), DataPart(data=data)]
        if text
        else [DataPart(data=data)],
        metadata=metadata,
    )


def answer_message(context_id: str, task_id: str, answer: BaseModel) -> Message:
    """A message answering a paused task's widget or review"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[DataPart(data=answer)],
    )


def tool_results_message(
    context_id: str, task_id: str, results: list[tuple[str, BaseModel]]
) -> Message:
    """A message resuming a paused task with each tool's result, under the interrupt
    id that asked for it"""
    return Message(
        message_id=uuid4().hex,
        context_id=context_id,
        task_id=task_id,
        parts=[
            DataPart(data=result, metadata={"interrupt_id": interrupt_id})
            for interrupt_id, result in results
        ],
    )


__all__ = ["answer_message", "new_message", "tool_results_message"]
