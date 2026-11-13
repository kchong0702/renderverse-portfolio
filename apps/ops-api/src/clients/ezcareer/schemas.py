from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Literal
from uuid import UUID

from document_schema import DocumentKind
from pydantic import BaseModel, ConfigDict, Field, JsonValue

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
    model: ModelChoice | None = Field(default=None, exclude_if=lambda v: v is None)
    """The model the user picked; None leaves it to ezcareer-harness"""


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


class Decision(BaseModel):
    type: Literal["approve", "reject"]
    """Whether the user lets the tool call run"""

    message: str | None = Field(default=None, exclude_if=lambda v: v is None)
    """Why the user rejected it, which the model gets; None says nothing"""


class Decisions(BaseModel):
    decisions: list[Decision]
    """One decision per tool call the paused task asked about, in its order"""


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


class Action(BaseModel):
    name: str
    """The tool the model called, such as update_profile"""

    args: dict[str, JsonValue]
    """The arguments the model gave it, not yet checked"""


class ReviewRequired(BaseModel):
    status: Literal["review_required"] = "review_required"
    """The run paused before tool calls the user must approve"""

    task_id: str
    """The paused task; the decisions go back on it"""

    actions: list[Action]
    """The tool calls waiting, in the order the decisions answer them"""


class NextScreen(BaseModel):
    label: str
    """The button's text, such as Add a fact in Portfolio"""

    screen: Literal["portfolio", "documents", "jobs", "settings"]
    """The screen the button opens"""


class Failed(BaseModel):
    status: Literal["failed"] = "failed"
    """The run stopped without a reply"""

    reason: str
    """Why, as ezcareer-harness put it"""

    next: NextScreen | None = None
    """Where the user adds what the run lacked; None when nothing would help"""


type Run[R] = Completed[R] | InputRequired | Failed
"""How a run of a harness executable ended"""


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    execute_tool: str
    """The tool a paused run asks ops-api to execute, such as documents; the rest
    are its arguments"""


type ExecuteTool = Callable[[ToolRequest], Awaitable[BaseModel]]
"""Executes the tool a run paused on, for the user the run is for, and returns
the tool result the run resumes with"""


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

    detail: str | None = None
    """Its result or target in plain words, such as 1 cover letter; None when unset"""


class StepUpdate(BaseModel):
    status: Literal["step"] = "step"
    """A step started, finished, failed or paused"""

    step: Step
    """The step as it stands"""


class Published(BaseModel):
    status: Literal["published"] = "published"
    """The run published an artifact other than its reply, its thinking or its
    text"""

    name: str
    """The artifact's name, such as changeset"""

    data: JsonValue
    """The artifact's one data part"""


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
    | Published
    | Completed[R]
    | InputRequired
    | ReviewRequired
    | Failed
    | Cancelled
)
"""One event of a streamed run: its start, its progress, then how it ended"""


__all__ = [
    "Action",
    "Answer",
    "Cancelled",
    "Completed",
    "Decision",
    "Decisions",
    "ExecuteTool",
    "Failed",
    "FamilyModels",
    "InputRequired",
    "ModelCatalog",
    "ModelChoice",
    "NextScreen",
    "Published",
    "RecordUsage",
    "ReviewRequired",
    "Run",
    "RunEvent",
    "RunMetadata",
    "Started",
    "Step",
    "StepUpdate",
    "Text",
    "Thinking",
    "ToolRequest",
    "Usage",
    "Widget",
]
