from __future__ import annotations

import httpx2

from src.adapters.job_sources.jsearch.client import JSearchClient
from src.adapters.job_sources.jsearch.schemas import JSearchJob, JSearchQuery
from src.adapters.job_sources.schemas import (
    JobPosting,
    JobQuery,
    JobSearchResults,
    PostingLine,
)
from src.core.config import JSearchSettings
from src.core.providers import Provider


def _jsearch_query(query: JobQuery) -> JSearchQuery:
    """JSearch's parameters for the search, with its location in the query"""
    return JSearchQuery(
        query=f"{query.query} in {query.location}" if query.location else query.query,
        country=query.country,
        work_from_home=query.remote_only,
        date_posted={None: "all", "day": "today", "week": "week", "month": "month"}[
            query.posted_within
        ],
        employment_types=[
            {
                "full_time": "FULLTIME",
                "part_time": "PARTTIME",
                "contract": "CONTRACTOR",
                "internship": "INTERN",
            }[kind]
            for kind in query.employment_types
        ],
        job_requirements=query.job_requirements,
        radius_km=query.radius_km,
        max_jobs=query.max_jobs,
    )


def _posting(job: JSearchJob) -> JobPosting:
    """The posting a JSearch result describes, its description numbered by line"""
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


class JSearchSource:
    provider = Provider.JSEARCH
    """Each user's JSearch key is their JSearch connection"""

    label = "JSearch"
    """JSearch's name as Settings shows it"""

    def __init__(
        self,
        settings: JSearchSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """JSearch as a job source, over one HTTP client for the app's lifetime"""
        self.encryption_key = settings.encryption_key
        """The Fernet key the users' JSearch keys are encrypted with"""

        self._client = JSearchClient(settings, transport)
        """JSearch's search API"""

    async def search(self, query: JobQuery, api_key: str) -> JobSearchResults:
        """JSearch's results for the query on the user's key as postings, with the
        key's quota from its headers; InvalidInput when JSearch refuses the key,
        ServiceUnavailable when it fails"""
        found = await self._client.search(api_key, _jsearch_query(query))
        return JobSearchResults(
            jobs=[_posting(job) for job in found.jobs],
            remaining=found.remaining,
            limit=found.limit,
        )

    async def aclose(self) -> None:
        """Close the HTTP client"""
        await self._client.aclose()


__all__ = ["JSearchSource"]
