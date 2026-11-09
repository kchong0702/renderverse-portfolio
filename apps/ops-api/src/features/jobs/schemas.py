from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.features.jobs.enums import JobStatus
from src.features.jobs.models import FitAnalysis


class JobCreate(BaseModel):
    external_id: str | None = Field(default=None, min_length=1, max_length=200)
    """The posting's id at its source; adding it again refreshes the stored job"""

    source: str = Field(default="", max_length=50)
    """Where the posting was found, such as JSearch"""

    title: str = Field(min_length=1, max_length=200)
    """Job title as posted"""

    company: str = Field(default="", max_length=200)
    """Employer name"""

    location: str = Field(default="", max_length=200)
    """Where the job is, such as Kuala Lumpur, hybrid"""

    salary: str = Field(default="", max_length=200)
    """Pay as the posting states it; empty when not stated"""

    url: str = Field(default="", max_length=2000)
    """Where to read the posting and apply"""

    posted_at: datetime | None = None
    """When the posting went up, if known"""

    analysis: FitAnalysis | None = None
    """How the posting fits the profile, when already analysed"""


class JobRead(JobCreate):
    id: UUID
    """The job's id"""

    status: JobStatus
    """Picked by the agent, saved or dismissed"""


class JobUpdate(BaseModel):
    status: JobStatus
    """Save, dismiss or return the job to the agent's picks"""


__all__ = ["JobCreate", "JobRead", "JobUpdate"]
