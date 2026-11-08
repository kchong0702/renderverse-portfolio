from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.shared.profile import CountryCode


class JSearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    query: str
    """Job title and key skills, with a city when the user wants one,
    such as "backend engineer python in London\""""

    country: CountryCode | None = None
    """ISO country code to search in, such as GB"""

    remote_only: bool = False
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
