from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.runner import ToolError
from src.db.session import session_scope
from src.features.jobs.enums import RunTrigger
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import JobRunCreate, JobRunQueued


class JobRunRequest(JobRunCreate):
    execute_tool: Literal["job_run"]
    """A paused run asks to queue a run of the job agent"""


async def job_run(
    factory: async_sessionmaker[AsyncSession], user_id: UUID, request: JobRunRequest
) -> JobRunQueued | ToolError:
    """Queue the agent run a paused run asks for, on a session of its own; ToolError
    while an agent run is queued"""
    async for session in session_scope(factory):
        try:
            queued = await JobRepository(session).queue_run(
                user_id, RunTrigger.AGENT, request.search, request.run_after
            )
            result = JobRunQueued(id=queued.id, run_after=queued.run_after)
        except IntegrityError:
            result = ToolError(error="A job agent run is already queued")
    return result


__all__ = ["JobRunRequest", "job_run"]
