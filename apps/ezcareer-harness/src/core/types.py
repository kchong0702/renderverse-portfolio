from pydantic import BaseModel, ConfigDict

from src.core.enums import Screen


class NextStep(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    label: str
    """The button's text, such as Add your experience"""

    screen: Screen
    """The screen the button opens"""
