from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from src.integrations.ezcareer.types import ModelFamily


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


__all__ = [
    "Answer",
    "Completed",
    "Failed",
    "FamilyModels",
    "InputRequired",
    "ModelCatalog",
    "ModelChoice",
    "Run",
    "RunMetadata",
    "Widget",
]
