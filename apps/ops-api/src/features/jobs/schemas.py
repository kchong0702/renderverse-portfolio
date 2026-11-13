from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, Field, computed_field

from src.features.documents import TailoredDocument
from src.features.jobs.enums import Importance, JobStatus, Match, RunStatus, RunTrigger
from src.features.profile import AgentProfile
from src.features.settings import SearchQuota


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

    seen_at: datetime | None
    """When the user first opened the job; None while it is new"""


class JobList(BaseModel):
    jobs: list[JobRead]
    """Every job, best fit first"""

    new_count: int
    """How many picks the user has not opened yet"""


class JobUpdate(BaseModel):
    status: JobStatus | None = None
    """Save, dismiss or return the job to the agent's picks; None leaves it"""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    """A new job title for a job added by hand; None leaves it"""

    company: str | None = Field(default=None, max_length=200)
    """A new employer name for a job added by hand; None leaves it"""

    seen: Literal[True] | None = None
    """Mark the job opened; one opened before keeps when it first was"""


class JobSearch(BaseModel):
    query: str | None = Field(default=None, max_length=200)
    """What to search for in place of the job agent's query"""

    location: str | None = Field(default=None, max_length=200)
    """Where to search in place of the job agent's location"""

    posted_within: Literal["day", "week", "month"] | None = None
    """Only postings this recent"""


class JobRunCreate(BaseModel):
    run_after: AwareDatetime | None = None
    """The earliest the run may start; None starts it as soon as a worker is free"""

    search: JobSearch | None = None
    """The search the run hands find-jobs; None searches from the preferences"""


class JobRunQueued(BaseModel):
    id: UUID
    """The queued run's id"""

    run_after: datetime
    """The earliest a worker may start it"""


class JobRunRead(BaseModel):
    id: UUID
    """The run's id"""

    trigger: RunTrigger
    """What queued the run: the daily schedule, the Find button or the assistant"""

    status: RunStatus
    """How far the run has got"""

    run_after: datetime
    """The earliest a worker may claim it"""

    found: int
    """How many jobs find-jobs returned"""

    new: int
    """How many of them were not stored before"""

    matched: int
    """How many of them fit at or above the user's min_score"""

    error: str
    """Why the last attempt failed; empty otherwise"""

    created_at: datetime
    """When it was queued"""

    finished_at: datetime | None
    """When it was done or failed; None while it is queued or running"""


class FindJobsInput(AgentProfile):
    search: JobSearch | None
    """Filters that replace the ones find-jobs builds from preferences"""


class AnalyseJobInput(AgentProfile):
    url: str
    """The posting analyse-job fetches and maps to the profile"""


class AnalyseJobOutput(BaseModel):
    analysis: FitAnalysis
    """How the posting fits; the harness also sends lines and filters, unread"""


class JobPosting(BaseModel):
    id: str
    """JSearch job id"""

    title: str
    """Job title"""

    company: str
    """Employer name"""

    location: str
    """City and country, as JSearch gives them"""

    remote: bool
    """Whether the job is remote"""

    posted_at: datetime | None
    """When the job was posted, if known"""

    apply_url: str
    """Where to apply"""


class MatchedJob(BaseModel):
    posting: JobPosting
    """The job as find-jobs' search returned it"""

    requirements: list[Requirement]
    """The agent's mapping of its requirements to the profile"""

    fit: int
    """Fit score from 0 to 100, computed by the harness"""


class FindJobsOutput(BaseModel):
    jobs: list[MatchedJob]
    """Jobs that fit the profile and preferences, best first"""

    quota: SearchQuota | None = None
    """JSearch's searches left, from its rate-limit headers; None when not sent"""


class TailorRead(BaseModel):
    resume: TailoredDocument
    """The job's résumé, copied from the master résumé"""

    cover_letter: TailoredDocument | None
    """The job's cover letter, copied from the master cover letter; None when
    there is no master cover letter, so only the résumé is tailored"""


__all__ = [
    "AnalyseJobInput",
    "AnalyseJobOutput",
    "FindJobsInput",
    "FindJobsOutput",
    "FitAnalysis",
    "JobCreate",
    "JobList",
    "JobRead",
    "JobRunCreate",
    "JobRunQueued",
    "JobRunRead",
    "JobSearch",
    "JobUpdate",
    "Requirement",
    "TailorRead",
]
