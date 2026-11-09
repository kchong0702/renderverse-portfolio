from typing import Literal

from pydantic import BaseModel, ConfigDict


class WidgetSetting(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

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


class ParentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    kind: Literal["question", "permission"]
    """A question wants an input back; a permission request wants accept back"""

    text: str
    """The question, or the action that needs permission"""


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    input: str | None = None
    """What was typed in the input field, if anything"""

    accept: bool | None = None
    """True for submit, False for cancel, None when neither was pressed"""
