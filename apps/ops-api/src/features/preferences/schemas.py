from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from src.features.preferences.enums import SalaryPeriod, WorkMode
from src.features.preferences.types import CountryCode, CurrencyCode


class Salary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(gt=0)
    """Amount before tax"""

    currency: CurrencyCode
    """ISO 4217 currency code"""

    period: SalaryPeriod
    """What the amount is paid for"""


class PreferencesRead(BaseModel):
    target_roles: str
    """The roles the user is looking for"""

    location: str
    """Where the job search looks"""

    countries: list[CountryCode]
    """Countries the user wants to work in; empty accepts any"""

    visa_free_countries: list[CountryCode]
    """Countries the user may work in without visa sponsorship"""

    work_modes: list[WorkMode]
    """Work modes the user accepts; empty accepts any"""

    min_salary: Salary | None
    """Lowest pay the user accepts; None when not set"""

    min_score: int
    """Lowest fit score, 0 to 100, a found job must reach"""

    run_at: time
    """When the daily job search starts"""


class PreferencesUpdate(BaseModel):
    target_roles: str | None = Field(default=None, max_length=200)
    """New roles to look for; None leaves them unchanged"""

    location: str | None = Field(default=None, max_length=200)
    """New search location; None leaves it unchanged"""

    countries: list[CountryCode] | None = None
    """Replaces the countries to work in; None leaves them unchanged"""

    visa_free_countries: list[CountryCode] | None = None
    """Replaces the visa-free countries; None leaves them unchanged"""

    work_modes: list[WorkMode] | None = None
    """Replaces the accepted work modes; None leaves them unchanged"""

    min_salary: Salary | None = None
    """New lowest pay, or null to clear it; left out leaves it unchanged"""

    min_score: int | None = Field(default=None, ge=0, le=100)
    """New minimum fit; None leaves it unchanged"""

    run_at: time | None = None
    """New daily search time; None leaves it unchanged"""


__all__ = ["PreferencesRead", "PreferencesUpdate", "Salary"]
