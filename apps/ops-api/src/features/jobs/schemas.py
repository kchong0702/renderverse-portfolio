from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, computed_field

from src.features.jobs.enums import Importance, JobStatus, Match


class Requirement(BaseModel):
    text: str = Field(min_length=1)
    """The requirement as the posting states it"""

    importance: Importance = Importance.REQUIRED
    """Whether the posting requires it or calls it nice to have"""

    match: Match
    """How well the profile meets it"""

    reason: str = ""
    """Why it is met, partly met or not met, in one sentence"""


class FitAnalysis(BaseModel):
    fit: int = Field(ge=0, le=100)
    """Fit score from 0 to 100, as analyse-job computes it"""

    requirements: list[Requirement] = Field(min_length=1)
    """Every requirement the posting states, mapped to the profile"""

    @computed_field
    @property
    def band(self) -> Literal["excellent", "good", "possible", "poor"]:
        """The fit score as a band, so the label always agrees with the score"""
        if self.fit >= 85:
            return "excellent"
        if self.fit >= 70:
            return "good"
        return "possible" if self.fit >= 50 else "poor"


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


__all__ = ["FitAnalysis", "JobCreate", "JobRead", "JobUpdate", "Requirement"]
