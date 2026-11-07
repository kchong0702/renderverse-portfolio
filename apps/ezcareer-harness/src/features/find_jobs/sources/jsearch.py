from datetime import datetime

import httpx
from pydantic import BaseModel, ConfigDict

from src.core.config import JSearchSettings
from src.features.analyse_job import PostingLine
from src.features.find_jobs.schemas import JobPosting
from src.features.find_jobs.types import DatePosted
from src.shared.models import CountryCode


class _Job(BaseModel):
    model_config = ConfigDict(extra="ignore", use_attribute_docstrings=True)

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


class _SearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", use_attribute_docstrings=True)

    data: list[_Job]
    """Jobs on the requested page"""


async def search(
    settings: JSearchSettings,
    query: str,
    country: CountryCode | None,
    remote_only: bool,
    date_posted: DatePosted,
) -> list[JobPosting]:
    """One page of JSearch results for the query"""
    if settings.api_key is None:
        raise RuntimeError("EZCAREER_HARNESS_JSEARCH__API_KEY is not set")
    params = {"query": query, "date_posted": date_posted, "work_from_home": remote_only}
    if country:
        params["country"] = country.lower()
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            str(settings.url),
            params=params,
            headers={
                "X-RapidAPI-Key": settings.api_key.get_secret_value(),
                "X-RapidAPI-Host": settings.url.host or "",
            },
        )
    response.raise_for_status()
    return [
        JobPosting(
            id=job.job_id,
            title=job.job_title,
            company=job.employer_name,
            location=", ".join(filter(None, [job.job_city, job.job_country])),
            country=job.job_country.upper()
            if job.job_country and len(job.job_country) == 2
            else None,
            remote=job.job_is_remote,
            posted_at=job.job_posted_at_datetime_utc,
            apply_url=job.job_apply_link,
            lines=[
                PostingLine(id=number, text=text)
                for number, text in enumerate(
                    filter(None, map(str.strip, job.job_description.splitlines())),
                    start=1,
                )
            ],
        )
        for job in _SearchResponse.model_validate_json(response.content).data
    ]
