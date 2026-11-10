from typing import Literal

from document_schema.types import Id
from pydantic import BaseModel, ConfigDict

from src.core.enums import Screen
from src.core.errors import ExecuteError
from src.core.types import NextStep
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


def require_facts(facts: list[ProfileFact]) -> None:
    """Fails the run with a way to Portfolio when the user has no profile facts"""
    if not facts:
        raise ExecuteError(
            "Your profile has no facts yet. Add your experience in Portfolio first.",
            NextStep(label="Add your experience", screen=Screen.PORTFOLIO),
        )
