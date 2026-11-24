from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, SerializeAsAny
from pydantic.alias_generators import to_camel

from src.clients.ezcareer.schemas import MessageMetadata, RunMetadata, Step, Usage


class TextPart(BaseModel):
    text: str
    """The user's words"""


class DataPart(BaseModel):
    data: SerializeAsAny[BaseModel]
    """The executable's input, or the answer to a paused task"""

    metadata: dict[str, str] | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """The interrupt_id of the paused tool call a tool result answers"""


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

    metadata: MessageMetadata | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """When and where the user wrote a new message; None on an answer or results"""


class SendMessageConfiguration(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, serialize_by_alias=True
    )

    return_immediately: bool
    """True answers with the task as soon as it exists, leaving it running"""


class SendMessageParams(BaseModel):
    message: Message
    """The message to send"""

    metadata: RunMetadata | None = Field(default=None, exclude_if=lambda v: v is None)
    """The user's model, and the user an agent's turn is for"""

    configuration: SendMessageConfiguration | None = Field(
        default=None, exclude_if=lambda v: v is None
    )
    """How the harness answers; None waits for the task to pause or end"""


class SendMessageRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    """JSON-RPC version"""

    id: str
    """Request id the response echoes"""

    method: Literal["SendMessage"] = "SendMessage"
    """Send the message; the answer comes once the task pauses or ends, or as soon
    as it exists with return_immediately"""

    params: SendMessageParams
    """The message"""


class Part(BaseModel):
    text: str | None = None
    """Set on a text part"""

    data: JsonValue = None
    """Set on a data part"""

    metadata: dict[str, JsonValue] | None = None
    """On a paused tool call's data part, the interrupt_id its result goes back under"""


class StatusMessage(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True)

    message_id: str = ""
    """The message's id, the same in every response that returns it"""

    parts: list[Part] = Field(min_length=1)
    """A reply's text, a failure's reason, or a pause's interrupts as data"""

    metadata: dict[str, JsonValue] | None = None
    """On the message ending a turn, the agent that answered and its document_id"""


class HistoryMessage(StatusMessage):
    message_id: str
    """The message's id, the same in every response that returns it"""


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

    history: list[HistoryMessage] = []
    """The task's earlier messages, each status message among them"""


class SendMessageResult(BaseModel):
    task: Task
    """The executor always answers with a task"""


class SendMessageSuccess(BaseModel):
    result: SendMessageResult
    """The task the message ran"""


class StepData(BaseModel):
    step: Step
    """A step of the run, which a working status carries"""


class UsageData(BaseModel):
    usage: Usage
    """A model call's usage, which a working status carries"""


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
    """One event of a SubscribeToTask stream"""


class TaskIdParams(BaseModel):
    id: str
    """The task to read or cancel"""


class TaskRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    """JSON-RPC version"""

    id: str
    """Request id, echoed in the response"""

    method: Literal["GetTask", "CancelTask", "SubscribeToTask"]
    """Read the task, cancel it, or stream its events from where it stands"""

    params: TaskIdParams
    """The task"""


class TaskSuccess(BaseModel):
    result: Task
    """The task as it stands"""


class ListTasksParams(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel, validate_by_name=True, serialize_by_alias=True
    )

    context_id: str
    """The context whose tasks to list"""

    status_timestamp_after: datetime
    """Only tasks whose status changed after this"""

    include_artifacts: bool = True
    """Return each task's artifacts, which hold a completed task's reply"""


class ListTasksRequest(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    """JSON-RPC version"""

    id: str
    """Request id, echoed in the response"""

    method: Literal["ListTasks"] = "ListTasks"
    """List a context's tasks"""

    params: ListTasksParams
    """Which tasks"""


class TaskList(BaseModel):
    tasks: list[Task] = []
    """The tasks found"""


class ListTasksSuccess(BaseModel):
    result: TaskList
    """The context's tasks"""


class RpcError(BaseModel):
    code: int
    """JSON-RPC error code"""

    message: str
    """Why the harness refused the request, such as an unknown or finished task"""


class SendMessageError(BaseModel):
    error: RpcError
    """The refusal"""


__all__ = [
    "Artifact",
    "DataPart",
    "ListTasksParams",
    "ListTasksRequest",
    "ListTasksSuccess",
    "Message",
    "SendMessageConfiguration",
    "SendMessageError",
    "SendMessageParams",
    "SendMessageRequest",
    "SendMessageSuccess",
    "StatusMessage",
    "StepData",
    "StreamSuccess",
    "Task",
    "TaskIdParams",
    "TaskRequest",
    "TaskStatus",
    "TaskSuccess",
    "TextPart",
    "UsageData",
]
