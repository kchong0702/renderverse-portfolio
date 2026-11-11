from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailMessage(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    sender: str
    """Who sent it, as the mail header names them"""

    sent_at: datetime
    """When it was sent"""

    text: str
    """The message's plain text; untrusted"""


class EmailThread(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    subject: str
    """The thread's subject; untrusted"""

    messages: list[EmailMessage] = Field(min_length=1)
    """Its messages, oldest first"""


class TimeSlot(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    start: datetime
    """When the slot starts"""

    end: datetime
    """When the slot ends"""
