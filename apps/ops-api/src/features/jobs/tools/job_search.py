from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.clients.jsearch import JSearchClient
from src.core.agent_runner import ToolError
from src.core.config import JSearchSettings
from src.core.exceptions import ServiceException
from src.db.session import session_scope
from src.features.jobs.jsearch import jsearch_query, postings
from src.features.jobs.schemas import JobSearchAnswer, JobSearchRequest
from src.features.preferences import PreferencesService
from src.features.settings import jsearch_connections


async def job_search(
    factory: async_sessionmaker[AsyncSession],
    client: JSearchClient,
    settings: JSearchSettings,
    user_id: UUID,
    request: JobSearchRequest,
) -> JobSearchAnswer | ToolError:
    """JSearch's postings that fit the user's preferences for a paused run's search,
    on their own key, keeping the quota, on a session of its own; ToolError without a key"""
    async for session in session_scope(factory):
        connections = jsearch_connections(session, settings)
        connection = await connections.get(user_id)
        if connection is None:
            result = ToolError(error="Connect JSearch in Settings to search for jobs")
        else:
            try:
                found = await client.search(
                    connections.secret(connection), jsearch_query(request)
                )
                await connections.record_quota(user_id, found.remaining, found.limit)
                result = JobSearchAnswer(
                    jobs=postings(
                        found.jobs, await PreferencesService(session).get(user_id)
                    ),
                    requests_left=found.remaining,
                )
            except ServiceException as error:
                result = ToolError(error=error.message)
    return result


__all__ = ["job_search"]
