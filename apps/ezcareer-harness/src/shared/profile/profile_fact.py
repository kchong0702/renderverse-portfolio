from typing import Literal

from document_schema.types import Id
from pydantic import BaseModel, ConfigDict

from src.shared.profile.types import YearMonth


class ProfileFact(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Key the agent cites as fact:<id>"""

    text: str
    """The fact as the user stated it"""

    start: YearMonth | None = None
    """When a job began; years of experience count these spans"""

    end: YearMonth | Literal["present"] | None = None
    """When the job ended, or present"""
