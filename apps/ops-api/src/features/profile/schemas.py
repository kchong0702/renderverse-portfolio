from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.features.profile.enums import EntryKind, SalaryPeriod, WorkMode
from src.features.profile.types import (
    CountryCode,
    CurrencyCode,
    EntryEnd,
    FactId,
    Highlight,
    Link,
    YearMonth,
)


class Salary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(gt=0)
    """Amount before tax"""

    currency: CurrencyCode
    """ISO 4217 currency code"""

    period: SalaryPeriod
    """What the amount is paid for"""


class Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_modes: list[WorkMode] = Field(default_factory=list)
    """Work modes the user accepts; empty accepts any"""

    countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user wants to work in; empty accepts any"""

    authorised_countries: list[CountryCode] = Field(default_factory=list)
    """Countries the user may work in without visa sponsorship"""

    min_salary: Salary | None = None
    """Lowest pay the user accepts"""


class ProfileRead(BaseModel):
    name: str
    """Full name as it goes on a résumé"""

    headline: str
    """One line under the name"""

    location: str
    """Where the user lives"""

    email: str
    """Contact email for documents"""

    phone: str
    """Contact phone for documents"""

    links: list[str]
    """Profile and portfolio URLs"""

    summary: str
    """A short paragraph about the user"""

    preferences: Preferences
    """What the user wants from a job"""


class ProfileUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    """New full name; None leaves it unchanged"""

    headline: str | None = Field(default=None, max_length=200)
    """New headline; None leaves it unchanged"""

    location: str | None = Field(default=None, max_length=200)
    """New location; None leaves it unchanged"""

    email: str | None = Field(default=None, max_length=320)
    """New contact email; None leaves it unchanged"""

    phone: str | None = Field(default=None, max_length=50)
    """New contact phone; None leaves it unchanged"""

    links: list[Link] | None = None
    """Replaces every link; None leaves them unchanged"""

    summary: str | None = None
    """New summary; None leaves it unchanged"""

    preferences: Preferences | None = None
    """Replaces every preference; None leaves them unchanged"""


class EntryWrite(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    """Job title, degree or project name"""

    organisation: str = Field(default="", max_length=200)
    """Employer, school, or who the project was for"""

    location: str = Field(default="", max_length=200)
    """Where it took place"""

    start: YearMonth | None = None
    """First month"""

    end: EntryEnd | None = None
    """Last month, or present; not before start"""

    summary: str = ""
    """One line about it; a project's tagline"""

    highlights: list[Highlight] = Field(default_factory=list)
    """What the user achieved, one sentence each"""

    archived: bool = False
    """Kept but left out of what the agents see"""

    on_site: bool = False
    """Shown on the portfolio site from the next release; only projects use it"""

    @model_validator(mode="after")
    def _end_not_before_start(self) -> Self:
        """Reject an end month earlier than the start month"""
        if self.start and self.end and self.end != "present" and self.end < self.start:
            raise ValueError("end must not be before start")
        return self


class EntryCreate(EntryWrite):
    kind: EntryKind
    """Role, education or project; fixed once created"""


class EntryRead(EntryCreate):
    id: UUID
    """The entry's id"""

    image_id: UUID | None = None
    """A project's cover image on the site, set through the portfolio"""

    video_id: UUID | None = None
    """A project's video on the site, set through the portfolio"""


class SkillWrite(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    """The skill or spoken language, such as Python or Malay"""

    group: str = Field(default="", max_length=100)
    """Heading it sits under, such as Platform or Spoken languages"""

    archived: bool = False
    """Kept but left out of what the agents see"""


class SkillRead(SkillWrite):
    id: UUID
    """The skill's id"""


class ProfileFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: FactId
    """Key the agents cite as fact:<id>"""

    text: str
    """The fact in the user's words"""

    start: YearMonth | None = None
    """When a job began; years of experience count these spans"""

    end: EntryEnd | None = None
    """When the job ended, or present"""


class AgentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    facts: list[ProfileFact]
    """What the user has done and knows, without archived items"""

    preferences: Preferences
    """What the user wants from a job"""


__all__ = [
    "AgentProfile",
    "EntryCreate",
    "EntryRead",
    "EntryWrite",
    "Preferences",
    "ProfileFact",
    "ProfileRead",
    "ProfileUpdate",
    "Salary",
    "SkillRead",
    "SkillWrite",
]
