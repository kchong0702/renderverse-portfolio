from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from src.shared.profile.enums import SalaryPeriod, WorkMode
from src.shared.profile.types import CountryCode


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
