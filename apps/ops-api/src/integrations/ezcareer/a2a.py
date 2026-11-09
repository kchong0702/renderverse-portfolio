from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, SerializeAsAny
from pydantic.alias_generators import to_camel

from src.integrations.ezcareer.schemas import RunMetadata


class TextPart(BaseModel):
    text: str
    """The user's words"""


class DataPart(BaseModel):
    data: SerializeAsAny[BaseModel]
    """The executable's input, or the answer to a paused task"""


class Message(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, serialize_by_alias=True
    )

    message_id: str
    """A fresh id per message"""

    role: Literal["ROLE_USER"] = "ROLE_USER"
    """Who sent it; ops-api always speaks for the user"""

    context_id: str
    """Groups a user's tasks; a task only takes messages in its own context"""

    task_id: str | None = Field(default=None, exclude_if=lambda v: v is None)
    """The paused task this answers; None starts a new task"""

    parts: list[TextPart | DataPart]
    """The text part becomes the run's messages; the data part its input"""


class SendMessageParams(BaseModel):
    message: Message
    """The message to send"""

    metadata: RunMetadata | None = Field(default=None, exclude_if=lambda v: v is None)
    """The user's model; on the request, which the task never keeps"""


class SendMessageRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    """JSON-RPC version"""

    id: str
    """Request id the response echoes"""

    method: Literal["SendMessage"] = "SendMessage"
    """A2A 1.0's blocking send; it answers once the task ends or pauses"""

    params: SendMessageParams
    """The message"""


class Part(BaseModel):
    text: str | None = None
    """Set on a text part"""

    data: JsonValue = None
    """Set on a data part"""


class StatusMessage(BaseModel):
    parts: list[Part] = Field(min_length=1)
    """A failure's reason as text, or a pause's interrupts as data"""


class TaskStatus(BaseModel):
    state: str
    """TASK_STATE_COMPLETED, TASK_STATE_INPUT_REQUIRED, TASK_STATE_FAILED and others"""

    message: StatusMessage | None = None
    """What the executor said with the state"""


class Artifact(BaseModel):
    parts: list[Part]
    """The reply, as one text or data part"""


class Task(BaseModel):
    id: str
    """The task's id, which a resume sends back"""

    status: TaskStatus
    """Where the task stands"""

    artifacts: list[Artifact] = []
    """The reply once the task completed"""


class SendMessageResult(BaseModel):
    task: Task
    """The executor always answers with a task"""


class SendMessageSuccess(BaseModel):
    result: SendMessageResult
    """The task the message ran"""


class RpcError(BaseModel):
    code: int
    """JSON-RPC error code"""

    message: str
    """Why the harness refused the request, such as an unknown or finished task"""


class SendMessageError(BaseModel):
    error: RpcError
    """The refusal"""


__all__ = [
    "DataPart",
    "Message",
    "SendMessageError",
    "SendMessageParams",
    "SendMessageRequest",
    "SendMessageSuccess",
    "TextPart",
]
