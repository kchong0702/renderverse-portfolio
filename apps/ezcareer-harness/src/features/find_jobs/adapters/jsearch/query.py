from pydantic import BaseModel, ConfigDict, Field

from src.features.find_jobs.adapters.jsearch.types import (
    DatePosted,
    EmploymentType,
    JobRequirement,
)
from src.shared.models import CountryCode


class JSearchQuery(BaseModel):
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
