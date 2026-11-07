from typing import Annotated, Literal

from document_schema.types import Id
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.shared.models.enums import SalaryPeriod, WorkMode
from src.shared.models.types import CountryCode

YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]


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


class Salary(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    amount: int = Field(gt=0)
    """Amount before tax"""

    currency: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    """ISO 4217 currency code, such as GBP"""

    period: SalaryPeriod
    """What the amount is paid for"""


class Preferences(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    work_modes: list[WorkMode] = Field(default_factory=list)
    """Work modes the user accepts; empty accepts any"""

    countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user wants to work in; empty accepts any"""

    authorised_countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user may work in without visa sponsorship"""

    min_salary: Salary | None = None
    """Lowest pay the user accepts"""


class Profile(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    facts: list[ProfileFact]
    """What the user has done and knows"""

    preferences: Preferences = Field(default_factory=Preferences)
    """What the user wants from a job"""
