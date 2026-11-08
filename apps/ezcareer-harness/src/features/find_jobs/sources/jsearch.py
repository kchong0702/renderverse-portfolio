from asyncio import sleep
from datetime import datetime

import httpx
from circuitbreaker import circuit
from pydantic import BaseModel, ConfigDict
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import JSearchSettings
from src.features.analyse_job import PostingLine
from src.features.find_jobs.schemas import JobPosting, JobQuery


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


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    postings: list[JobPosting]
    """The jobs found, in JSearch's order"""

    requests_left: int | None
    """JSearch requests left this month, from RapidAPI's quota header"""


class _Page(BaseModel):
    model_config = ConfigDict(extra="ignore", use_attribute_docstrings=True)

    jobs: list[_Job]
    """Jobs on the requested page"""

    cursor: str | None = None
    """Where the next page starts; None on the last page"""


class _SearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore", use_attribute_docstrings=True)

    data: _Page
    """The requested page"""


def _retryable(error: BaseException) -> bool:
    """Whether a failed page is worth asking for again: JSearch rate-limited it,
    was down or never answered"""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {429, 500, 502, 503}
    return isinstance(error, httpx.TransportError)


@circuit(
    failure_threshold=3,
    recovery_timeout=60,
    expected_exception=httpx.HTTPError,
    name="jsearch",
)
async def _page(
    client: httpx.AsyncClient, settings: JSearchSettings, params: dict
) -> httpx.Response:
    """One page of results, retried twice with backoff; after three failed pages
    in a row the circuit opens and calls fail at once for a minute"""
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(_retryable),
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=4),
        sleep=lambda seconds: sleep(seconds),
        reraise=True,
    ):
        with attempt:
            response = await client.get(
                str(settings.url),
                params=params,
                headers={
                    "X-RapidAPI-Key": settings.api_key.get_secret_value(),
                    "X-RapidAPI-Host": settings.url.host or "",
                },
            )
            response.raise_for_status()
    return response


async def search(settings: JSearchSettings, query: JobQuery) -> SearchResult:
    """Up to query.max_jobs JSearch results, ten a page, following JSearch's cursor
    until it has enough or runs out"""
    if settings.api_key is None:
        raise RuntimeError("EZCAREER_HARNESS_JSEARCH__API_KEY is not set")
    params: dict = {
        "query": query.query,
        "date_posted": query.date_posted,
        "work_from_home": query.remote_only,
    }
    if query.country:
        params["country"] = query.country.lower()
    if query.employment_types:
        params["employment_types"] = ",".join(query.employment_types)
    if query.job_requirements:
        params["job_requirements"] = ",".join(query.job_requirements)
    if query.radius_km:
        params["radius"] = query.radius_km
    postings: list[JobPosting] = []
    cursor = None
    async with httpx.AsyncClient(timeout=30) as client:
        while len(postings) < query.max_jobs:
            response = await _page(
                client, settings, params | ({"cursor": cursor} if cursor else {})
            )
            page = _SearchResponse.model_validate_json(response.content).data
            postings += [_posting(job) for job in page.jobs]
            cursor = page.cursor
            if not cursor or not page.jobs:
                break
    left = response.headers.get("x-ratelimit-requests-remaining")
    return SearchResult(
        postings=postings[: query.max_jobs],
        requests_left=int(left) if left else None,
    )


def _posting(job: _Job) -> JobPosting:
    """A JSearch job as a posting, its description numbered line by line"""
    return JobPosting(
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
