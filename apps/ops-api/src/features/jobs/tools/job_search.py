from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.adapters.job_sources import JobPosting, JobQuery, JobSource
from src.core.agent_runner import ToolError
from src.core.exceptions import Conflict, ServiceException
from src.features.connections import ConnectionService, api_key_connections
from src.features.jobs.schemas import JobSearchAnswer
from src.features.preferences import PreferencesRead, PreferencesService, WorkMode


class JobSearchRequest(JobQuery):
    execute_tool: Literal["job_search"]
    """A paused run asks ops-api to search for jobs on the user's key"""


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


def _kept(postings: list[JobPosting], preferences: PreferencesRead) -> list[JobPosting]:
    """The postings newest first, each job once and none that breaks the user's
    work mode or country preferences"""
    unique: dict[tuple[str, str, str], JobPosting] = {}
    for posting in sorted(
        postings,
        key=lambda p: p.posted_at or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    ):
        unique.setdefault(
            (posting.title.casefold(), posting.company.casefold(), posting.location),
            posting,
        )
    return [posting for posting in unique.values() if _fits(posting, preferences)]


def _connections(session: AsyncSession, source: JobSource) -> ConnectionService:
    """The users' keys to the source on the session"""
    return api_key_connections(
        session, source.provider, source.encryption_key, source.label
    )


async def source_key(session: AsyncSession, source: JobSource, user_id: UUID) -> str:
    """The user's key to the source; Conflict naming the source when they have not
    connected it or it can no longer be read"""
    connections = _connections(session, source)
    connection = await connections.get(user_id)
    if connection is None:
        raise Conflict(f"Connect {source.label} in Settings to search for jobs")
    return connections.secret(connection)


async def job_search(
    factory: async_sessionmaker[AsyncSession],
    source: JobSource,
    user_id: UUID,
    request: JobSearchRequest,
) -> JobSearchAnswer | ToolError:
    """The source's postings that fit the user's preferences for a paused run's
    search, on their own key, keeping the quota; no session is open while it searches"""
    try:
        async with factory() as session:
            api_key = await source_key(session, source, user_id)
        found = await source.search(request, api_key)
    except ServiceException as error:
        return ToolError(error=error.message)
    async with factory() as session, session.begin():
        await _connections(session, source).record_quota(
            user_id, found.remaining, found.limit
        )
        preferences = await PreferencesService(session).get(user_id)
    return JobSearchAnswer(
        jobs=_kept(found.jobs, preferences), requests_left=found.remaining
    )


__all__ = ["JobSearchRequest", "job_search", "source_key"]
