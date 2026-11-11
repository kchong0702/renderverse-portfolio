from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal
from uuid import UUID

from document_schema import DocumentKind
from pydantic import BaseModel, ConfigDict, Field

from src.clients.ezcareer.types import ModelFamily


class FamilyModels(BaseModel):
    family: ModelFamily
    """The provider"""

    models: list[str]
    """Model names ezcareer-harness offers for it"""


class ModelCatalog(BaseModel):
    families: list[FamilyModels]
    """Every provider ezcareer-harness offers, with its models"""


class ModelChoice(BaseModel):
    family: ModelFamily
    """The model's provider"""

    model: str = Field(min_length=1, max_length=100)
    """A model ezcareer-harness offers for that provider"""


class RunMetadata(BaseModel):
    model: ModelChoice
    """The model the user picked"""


class Widget(BaseModel):
    label: str | None = None
    """Text the widget shows; shown only when set"""

    input_value: str | None = None
    """A value shown in a disabled input field; shown only when set"""

    input_placeholder: str | None = None
    """Placeholder of an input field the user types in; shown only when set"""

    submit_btn: str | None = None
    """Text of the submit button; shown only when set"""

    cancel_btn: str | None = None
    """Text of the cancel button; shown only when set"""

    choose: Literal["document"] | None = None
    """What the user picks instead of typing; the app lists their documents"""

    kind: DocumentKind | None = None
    """The kind of document to list for choose; every kind when None"""


class Answer(BaseModel):
    input: str | None = None
    """What the user typed in the widget's input field, if anything"""

    accept: bool | None = None
    """True for submit, False for cancel, None when neither was pressed"""


class Completed[R](BaseModel):
    status: Literal["completed"] = "completed"
    """The run finished"""

    reply: R
    """The executable's reply: an agent's text, or a workflow's output"""


class InputRequired(BaseModel):
    status: Literal["input_required"] = "input_required"
    """The run paused to ask the user something"""

    task_id: str
    """The paused task; the answer goes back on it"""

    widget: Widget
    """What to ask the user"""


class Failed(BaseModel):
    status: Literal["failed"] = "failed"
    """The run stopped without a reply"""

    reason: str
    """Why, as ezcareer-harness put it"""


type Run[R] = Completed[R] | InputRequired | Failed
"""How a run of a harness executable ended"""


class DataRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    fetch: str
    """What a paused run asks ops-api for, such as documents; the rest are its
    arguments"""


type AnswerDataRequest = Callable[[DataRequest], Awaitable[BaseModel]]
"""Answers the data request a run paused with, for the user the run is for"""


class Started(BaseModel):
    status: Literal["started"] = "started"
    """The run started"""

    task_id: str
    """The run's task, which Stop cancels"""


class Thinking(BaseModel):
    status: Literal["thinking"] = "thinking"
    """The model reasoned"""

    turn: str
    """The model turn the reasoning belongs to"""

    text: str
    """The next piece of the reasoning's summary"""


class Text(BaseModel):
    status: Literal["text"] = "text"
    """The model wrote"""

    turn: str
    """The model turn the text belongs to"""

    text: str
    """The next piece of the text"""


class Step(BaseModel):
    id: str
    """The tool call or graph task the step is"""

    parent: str | None
    """The tool call whose workflow runs this step, if any"""

    name: str
    """The tool or graph node, such as analyse_job or fetch"""

    status: Literal["running", "done", "failed", "waiting"]
    """Where the step is"""


class StepUpdate(BaseModel):
    status: Literal["step"] = "step"
    """A step started, finished, failed or paused"""

    step: Step
    """The step as it stands"""


class Cancelled(BaseModel):
    status: Literal["cancelled"] = "cancelled"
    """The user stopped the run"""


class Usage(BaseModel):
    provider: str
    """The model's family, such as claude"""

    model: str
    """The model the call asked for"""

    agent: str
    """The harness agent whose model made the call"""

    node: str
    """The graph node that made the call"""

    input_tokens: int
    """Input tokens, cache reads and writes included"""

    output_tokens: int
    """Output tokens, reasoning included"""

    cache_read_tokens: int
    """Input tokens read from the prompt cache"""

    cache_write_tokens: int
    """Input tokens written to the prompt cache"""

    reasoning_tokens: int
    """Output tokens spent reasoning"""

    latency_ms: int
    """How long the call took"""

    stop_reason: str | None
    """Why the provider stopped"""

    request_id: str | None
    """The provider's id for the response"""


type RecordUsage = Callable[[UUID, str, str, Usage], Awaitable[None]]
"""Keeps a user's model call, given the thread and A2A task it ran in"""


type RunEvent[R] = (
    Started
    | Thinking
    | Text
    | StepUpdate
    | Completed[R]
    | InputRequired
    | Failed
    | Cancelled
)
"""One event of a streamed run: its start, its progress, then how it ended"""


__all__ = [
    "Answer",
    "AnswerDataRequest",
    "Cancelled",
    "Completed",
    "DataRequest",
    "Failed",
    "FamilyModels",
    "InputRequired",
    "ModelCatalog",
    "ModelChoice",
    "RecordUsage",
    "Run",
    "RunEvent",
    "RunMetadata",
    "Started",
    "Step",
    "StepUpdate",
    "Text",
    "Thinking",
    "Usage",
    "Widget",
]
