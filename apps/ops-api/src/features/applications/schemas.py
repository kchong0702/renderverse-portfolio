from __future__ import annotations

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.db.base import as_utc
from src.features.applications.enums import (
    ApplicationStage,
    NextStepFormat,
    StepKind,
    StepStatus,
)


class ApplicationWrite(BaseModel):
    stage: ApplicationStage = ApplicationStage.DRAFT
    """Where it stands in the pipeline"""

    applied_on: date | None = None
    """The day it was sent"""


class ApplicationUpdate(ApplicationWrite):
    company: str | None = Field(default=None, max_length=200)
    """Employer applied to, saved on a job added by hand; None leaves it"""

    role: str | None = Field(default=None, min_length=1, max_length=200)
    """Job title applied for, saved on a job added by hand; None leaves it"""


class JobApplicationCreate(ApplicationWrite):
    model_config = ConfigDict(extra="forbid")

    job_id: UUID
    """The stored job it is for; fixed once created"""


class ManualApplicationCreate(ApplicationWrite):
    model_config = ConfigDict(extra="forbid")

    company: str = Field(min_length=1, max_length=200)
    """Employer applied to"""

    role: str = Field(min_length=1, max_length=200)
    """Job title applied for"""

    url: str = Field(default="", max_length=2000)
    """Where the posting is, if known"""

    location: str = Field(default="", max_length=200)
    """Where the job is, if known"""


class StepWrite(BaseModel):
    kind: StepKind
    """An interview, a follow-up, a take-home or an offer deadline"""

    title: str = Field(default="", max_length=200)
    """What it is, such as Technical interview; empty to go by its kind"""

    starts_at: AwareDatetime | None = None
    """When it starts, with its offset; None for a step that only has a due day"""

    ends_at: AwareDatetime | None = None
    """When it ends, with its offset, if known"""

    due_on: date | None = None
    """The day it must be done by, such as a take-home's deadline"""

    format: NextStepFormat | None = None
    """Whether it is a video call, a phone call or on site"""

    location: str | None = Field(default=None, max_length=500)
    """Where it happens, such as an address or a meeting link"""

    status: StepStatus = StepStatus.OPEN
    """Open, done or cancelled"""

    @model_validator(mode="after")
    def _has_a_time(self) -> Self:
        """Reject a step with neither a start nor a due day, or an end without a
        start or before it"""
        if self.starts_at is None and self.due_on is None:
            raise ValueError("A step needs starts_at or due_on")
        if self.ends_at is not None and (
            self.starts_at is None or self.ends_at < self.starts_at
        ):
            raise ValueError("A step's ends_at needs a starts_at no later than it")
        return self


class StepRead(StepWrite):
    id: UUID
    """The step's id"""

    application_id: UUID
    """The application it belongs to"""

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def _in_utc(cls, moment: datetime | None) -> datetime | None:
        """The time, taking one without a zone as UTC"""
        return moment and as_utc(moment)


class ApplicationRead(ApplicationWrite):
    id: UUID
    """The application's id"""

    job_id: UUID
    """The job it is for"""

    company: str
    """Employer applied to, from the job"""

    role: str
    """Job title applied for, from the job"""

    by_hand: bool
    """Whether its job was added by hand with it"""

    fit: int | None = None
    """The job's fit score; None until the job is analysed"""

    next_step: StepRead | None = None
    """The soonest open step still ahead; None when there is none"""

    overdue: list[StepRead] = Field(default_factory=list)
    """Open steps whose due day has passed, oldest first"""

    offer_deadline: date | None = None
    """The due day of the open offer deadline step; None when there is none"""


__all__ = [
    "ApplicationRead",
    "ApplicationUpdate",
    "ApplicationWrite",
    "JobApplicationCreate",
    "ManualApplicationCreate",
    "StepRead",
    "StepWrite",
]
