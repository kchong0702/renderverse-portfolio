from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class JSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    """Job title and key skills, with a city when the user wants one"""

    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    """ISO country code to search in, such as GB"""

    work_from_home: bool = False
    """Return only remote jobs"""

    date_posted: Literal["all", "today", "3days", "week", "month"] = "week"
    """How recent the jobs must be"""

    employment_types: list[Literal["FULLTIME", "CONTRACTOR", "PARTTIME", "INTERN"]] = (
        Field(default_factory=list)
    )
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
    """How far from the city in the query a job may be"""

    max_jobs: int = Field(default=30, ge=10, le=50, multiple_of=10)
    """How many jobs to fetch"""


class JSearchJob(BaseModel):
    job_id: str
    """JSearch job id"""

    job_title: str
    """Job title"""

    employer_name: str
    """Employer name"""

    job_city: str | None = None
    """City, if given"""

    job_country: str | None = None
    """Country code, if given"""

    job_is_remote: bool = False
    """Whether the job is remote"""

    job_posted_at_datetime_utc: datetime | None = None
    """When the job was posted"""

    job_apply_link: str
    """Where to apply"""

    job_description: str = ""
    """Plain text description"""


class JSearchPage(BaseModel):
    jobs: list[JSearchJob]
    """The page's results"""

    cursor: str | None = None
    """Where the next page starts; None on the last page"""


class JSearchResponse(BaseModel):
    data: JSearchPage
    """The requested page"""


class JSearchResults(BaseModel):
    jobs: list[JSearchJob]
    """JSearch's results in its order, at most the query's max_jobs"""

    remaining: int | None
    """Requests the key has left this period, if JSearch said"""

    limit: int | None
    """Requests the key allows this period, if JSearch said"""


__all__ = [
    "JSearchJob",
    "JSearchPage",
    "JSearchQuery",
    "JSearchResponse",
    "JSearchResults",
]
