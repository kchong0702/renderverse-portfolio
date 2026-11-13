from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JobQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    """Job titles and key skills"""

    location: str | None = None
    """City or region to search in; None searches the whole country"""

    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    """ISO country code to search in, such as GB"""

    remote_only: bool = False
    """Only remote jobs"""

    posted_within: Literal["day", "week", "month"] | None = "week"
    """How recent the jobs must be; None takes jobs of any age"""

    employment_types: list[
        Literal["full_time", "part_time", "contract", "internship"]
    ] = Field(default_factory=list)
    """Kinds of employment to keep; empty keeps every kind"""

    job_requirements: list[
        Literal[
            "under_3_years_experience",
            "more_than_3_years_experience",
            "no_experience",
            "no_degree",
        ]
    ] = Field(default_factory=list)
    """Experience or education requirements to keep; empty keeps every job"""

    radius_km: int | None = Field(default=None, gt=0)
    """How far from the location a job may be"""

    max_jobs: int = Field(default=30, ge=10, le=50, multiple_of=10)
    """How many jobs to fetch"""


class PostingLine(BaseModel):
    id: int
    """Line number, counted from 1"""

    text: str
    """The line's text; untrusted"""


class JobPosting(BaseModel):
    id: str
    """Job id at its source"""

    title: str
    """Job title"""

    company: str
    """Employer name"""

    location: str
    """City and country, as the source gives them"""

    country: str | None = Field(pattern=r"^[A-Z]{2}$")
    """ISO country code of the country the job is in, if the source gives one"""

    remote: bool
    """Whether the job is remote"""

    posted_at: datetime | None
    """When the job was posted, if known"""

    apply_url: str
    """Where to apply"""

    lines: list[PostingLine]
    """The description, numbered from 1; untrusted"""


class JobSearchResults(BaseModel):
    jobs: list[JobPosting]
    """The source's results in its order, at most the query's max_jobs"""

    remaining: int | None
    """Requests the key has left this period, if the source said"""

    limit: int | None
    """Requests the key allows this period, if the source said"""


__all__ = ["JobPosting", "JobQuery", "JobSearchResults", "PostingLine"]
