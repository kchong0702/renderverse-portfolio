from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, SerializeAsAny
from pydantic.alias_generators import to_camel

from src.clients.ezcareer.schemas import RunMetadata, Step


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

    method: Literal["SendMessage", "SendStreamingMessage"] = "SendMessage"
    """SendMessage answers once the task ends or pauses; SendStreamingMessage streams
    each event"""

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
    state: Literal[
        "TASK_STATE_SUBMITTED",
        "TASK_STATE_WORKING",
        "TASK_STATE_INPUT_REQUIRED",
        "TASK_STATE_AUTH_REQUIRED",
        "TASK_STATE_COMPLETED",
        "TASK_STATE_CANCELED",
        "TASK_STATE_FAILED",
        "TASK_STATE_REJECTED",
    ]
    """Where the task stands, as A2A 1.0 names it"""

    message: StatusMessage | None = None
    """What the executor said with the state"""


class Artifact(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    artifact_id: str = ""
    """Which artifact a streamed chunk appends to, such as text-<turn>"""

    name: str = ""
    """The executable's name on its reply; thinking or text on a streamed turn"""

    parts: list[Part]
    """The reply as one text or data part, or a streamed chunk's text"""


class Task(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    id: str
    """The task's id, which a resume sends back"""

    context_id: str = ""
    """The context the task runs in, which names its user"""

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


class StepData(BaseModel):
    step: Step
    """A step of the run, which a working status carries"""


class StatusUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    task_id: str
    """The task the update is about"""

    status: TaskStatus
    """Where the task stands now; a working status may carry a step"""


class ArtifactUpdate(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    task_id: str
    """The task the chunk belongs to"""

    artifact: Artifact
    """The chunk, appended to the artifact with its id"""


class StreamResult(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    task: Task | None = None
    """The task, sent first when a new task starts"""

    status_update: StatusUpdate | None = None
    """A change of the task's status"""

    artifact_update: ArtifactUpdate | None = None
    """A chunk of an artifact"""


class StreamSuccess(BaseModel):
    result: StreamResult
    """One event of a SendStreamingMessage stream"""


class TaskIdParams(BaseModel):
    id: str
    """The task to read or cancel"""


class TaskRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    """JSON-RPC version"""

    id: str
    """Request id, echoed in the response"""

    method: Literal["GetTask", "CancelTask"]
    """Read the task, or cancel it"""

    params: TaskIdParams
    """The task"""


class TaskSuccess(BaseModel):
    result: Task
    """The task as it stands"""


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
    "StepData",
    "StreamSuccess",
    "TaskIdParams",
    "TaskRequest",
    "TaskSuccess",
    "TextPart",
]
