from datetime import datetime

import httpx
from circuitbreaker import CircuitBreaker, CircuitBreakerError
from pydantic import BaseModel, ConfigDict
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from src.core.config import JSearchSettings
from src.features.analyse_job import PostingLine
from src.features.find_jobs.adapters.exceptions import SourceUnavailable
from src.features.find_jobs.adapters.jsearch.query import JSearchQuery
from src.features.find_jobs.adapters.protocol import SearchResult
from src.features.find_jobs.schemas import JobPosting


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


def retryable(error: BaseException) -> bool:
    """Whether JSearch rate-limited a page, was down or never answered"""
    if isinstance(error, httpx.HTTPStatusError):
        return error.response.status_code in {429, 500, 502, 503}
    return isinstance(error, httpx.TransportError)


async def _page(
    client: httpx.AsyncClient,
    settings: JSearchSettings,
    params: dict[str, str | int | bool],
) -> httpx.Response:
    """One page of results, tried again with backoff while retryable"""
    async for attempt in AsyncRetrying(
        retry=retry_if_exception(retryable),
        stop=stop_after_attempt(settings.retry_attempts),
        wait=wait_exponential(max=settings.retry_max_wait_seconds),
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


async def search(
    settings: JSearchSettings, circuit: CircuitBreaker, query: JSearchQuery
) -> SearchResult:
    """Up to query.max_jobs JSearch results, following JSearch's cursor until it
    has enough or runs out, each page through the circuit"""
    if settings.api_key is None:
        raise SourceUnavailable("EZCAREER_HARNESS_JSEARCH__API_KEY is not set")
    params: dict[str, str | int | bool] = {
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
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds) as client:
            while len(postings) < query.max_jobs:
                response = await circuit.decorate(_page)(
                    client, settings, params | ({"cursor": cursor} if cursor else {})
                )
                page = _SearchResponse.model_validate_json(response.content).data
                postings += [
                    JobPosting(
                        id=job.job_id,
                        title=job.job_title,
                        company=job.employer_name,
                        location=", ".join(
                            filter(None, [job.job_city, job.job_country])
                        ),
                        country=job.job_country.upper()
                        if job.job_country and len(job.job_country) == 2
                        else None,
                        remote=job.job_is_remote,
                        posted_at=job.job_posted_at_datetime_utc,
                        apply_url=job.job_apply_link,
                        lines=[
                            PostingLine(id=number, text=text)
                            for number, text in enumerate(
                                filter(
                                    None,
                                    map(str.strip, job.job_description.splitlines()),
                                ),
                                start=1,
                            )
                        ],
                    )
                    for job in page.jobs
                ]
                cursor = page.cursor
                if not cursor or not page.jobs:
                    break
    except CircuitBreakerError as error:
        raise SourceUnavailable(
            "JSearch is paused after repeated failures; try again in "
            f"{circuit.open_remaining}s"
        ) from error
    except httpx.HTTPStatusError as error:
        raise SourceUnavailable(
            f"JSearch answered {error.response.status_code}: {error.response.text}"
        ) from error
    except httpx.HTTPError as error:
        raise SourceUnavailable(
            f"JSearch failed, try again later: {type(error).__name__} {error}"
        ) from error
    left = response.headers.get("x-ratelimit-requests-remaining")
    return SearchResult(
        postings=postings[: query.max_jobs],
        requests_left=int(left) if left else None,
    )
