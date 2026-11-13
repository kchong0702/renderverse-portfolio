from __future__ import annotations

from datetime import UTC, datetime

from src.clients.jsearch import JSearchJob, JSearchQuery
from src.features.jobs.schemas import JobPosting, JobSearchRequest, PostingLine
from src.features.preferences import PreferencesRead, WorkMode


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


def _fits(posting: JobPosting, preferences: PreferencesRead) -> bool:
    """Whether the posting is in a work mode and country the user accepts"""
    modes = {WorkMode.REMOTE} if posting.remote else {WorkMode.ONSITE, WorkMode.HYBRID}
    return (
        not preferences.work_modes or bool(modes & set(preferences.work_modes))
    ) and (
        posting.country is None
        or not preferences.countries
        or posting.country in preferences.countries
    )


def jsearch_query(request: JobSearchRequest) -> JSearchQuery:
    """JSearch's parameters for the search, with its location in the query"""
    return JSearchQuery(
        query=f"{request.query} in {request.location}"
        if request.location
        else request.query,
        country=request.country,
        work_from_home=request.remote_only,
        date_posted={None: "all", "day": "today", "week": "week", "month": "month"}[
            request.posted_within
        ],
        employment_types=[
            {
                "full_time": "FULLTIME",
                "part_time": "PARTTIME",
                "contract": "CONTRACTOR",
                "internship": "INTERN",
            }[kind]
            for kind in request.employment_types
        ],
        job_requirements=request.job_requirements,
        radius_km=request.radius_km,
        max_jobs=request.max_jobs,
    )


def postings(jobs: list[JSearchJob], preferences: PreferencesRead) -> list[JobPosting]:
    """JSearch's results as postings, newest first, each job once and none that
    breaks the user's work mode or country preferences"""
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        map(_posting, jobs),
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        unique.setdefault(
            (posting.title.casefold(), posting.company.casefold(), posting.location),
            posting,
        )
    return [posting for posting in unique.values() if _fits(posting, preferences)]
