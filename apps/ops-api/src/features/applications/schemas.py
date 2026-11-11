from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.features.applications.enums import ApplicationStage, NextStepFormat


class ApplicationWrite(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    """Employer applied to"""

    role: str = Field(min_length=1, max_length=200)
    """Job title applied for"""

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


class ApplicationCreate(ApplicationWrite):
    job_id: UUID | None = None
    """The stored job it is for; fixed once created"""


class ApplicationRead(ApplicationCreate):
    id: UUID
    """The application's id"""

    fit: int | None = None
    """The job's fit score; None without an analysed job"""


__all__ = ["ApplicationCreate", "ApplicationRead", "ApplicationWrite"]
