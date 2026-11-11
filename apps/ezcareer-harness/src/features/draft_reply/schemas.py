from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class Application(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    company: str
    """The employer applied to"""

    role: str
    """The job applied for"""

    stage: str
    """Where the application is, such as applied"""

    applied_at: date | None = None
    """When the user applied, if known"""


class DraftReply(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    body: str
    """The plain-text email the user sends"""

    slot_ids: list[int] = Field(default_factory=list)
    """Ids of the free slots the email offers; empty when it offers no times"""
