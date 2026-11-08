from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.features.analyse_job import PostingLine, Requirement, fit_score
from src.features.find_jobs.types import DatePosted, EmploymentType, JobRequirement
from src.shared.models import CountryCode


class JobQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    query: str
    """Job title and key skills, with a city when the user wants one,
    such as "backend engineer python in London\""""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB"""

    remote_only: bool = False
    """Return only remote jobs"""

    date_posted: DatePosted = "week"
    """How recent the jobs must be"""

    employment_types: list[EmploymentType] = Field(default_factory=list)
    """Kinds of employment to keep; empty keeps every kind"""

    job_requirements: list[JobRequirement] = Field(default_factory=list)
    """Experience or education requirements to keep; empty keeps every job"""

    radius_km: int | None = Field(default=None, gt=0)
    """How far from the city in the query a job may be"""

    max_jobs: int = Field(default=30, ge=10, le=50, multiple_of=10)
    """How many jobs to fetch; every 10 costs one of the month's JSearch requests"""


class JobPosting(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: str
    """JSearch job id"""

    title: str
    """Job title"""

    company: str
    """Employer name"""

    location: str
    """City and country, as JSearch gives them"""

    country: CountryCode | None
    """Country the job is in, if JSearch gives one"""

    remote: bool
    """Whether the job is remote"""

    posted_at: datetime | None
    """When the job was posted, if known"""

    apply_url: str
    """Where to apply"""

    lines: list[PostingLine]
    """The description, numbered from 1; untrusted"""


class RankedJob(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    job_id: str
    """Id of a job search_jobs returned"""

    requirements: list[Requirement] = Field(min_length=1)
    """Every requirement in the description, mapped to the profile"""


class RankedJobs(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    jobs: list[RankedJob]
    """Jobs that fit the profile and preferences, best first"""


class MatchedJob(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    posting: JobPosting
    """The job as search_jobs returned it"""

    requirements: list[Requirement]
    """The agent's mapping of its requirements"""

    @computed_field
    @property
    def fit(self) -> int:
        """Fit score from 0 to 100, computed from the requirements"""
        return fit_score(self.requirements)
