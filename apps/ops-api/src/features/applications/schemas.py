from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.features.applications.enums import ApplicationStage, NextStepFormat


class ApplicationWrite(BaseModel):
    stage: ApplicationStage = ApplicationStage.DRAFT
    """Where it stands in the pipeline"""

    applied_on: date | None = None
    """The day it was sent"""

    next_step: str = Field(default="", max_length=200)
    """What happens next, such as Technical interview or Follow up"""

    next_step_at: datetime | None = None
    """When the next step is due or booked"""

    next_step_due: date | None = None
    """The day the next step must be done by, such as a take-home's deadline"""

    next_step_format: NextStepFormat | None = None
    """Whether the next step is a video call, a phone call or on site"""

    next_step_location: str | None = Field(default=None, max_length=200)
    """Where the next step happens, such as an address or a meeting link"""


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


__all__ = [
    "ApplicationRead",
    "ApplicationUpdate",
    "ApplicationWrite",
    "JobApplicationCreate",
    "ManualApplicationCreate",
]
