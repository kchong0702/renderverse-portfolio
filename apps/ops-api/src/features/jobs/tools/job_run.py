from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.agent_runner import ToolError
from src.features.jobs.enums import RunTrigger
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import JobRunCreate, JobRunQueued


class JobRunRequest(JobRunCreate):
    execute_tool: Literal["job_run"]
    """A paused run asks to queue a run of the job agent"""


async def job_run(
    session: AsyncSession, user_id: UUID, request: JobRunRequest
) -> JobRunQueued | ToolError:
    """Queue the agent run a paused run asks for on the session; ToolError while an
    agent run is queued"""
    try:
        queued = await JobRepository(session).queue_run(
            user_id, RunTrigger.AGENT, request.search, request.run_after
        )
    except IntegrityError:
        return ToolError(error="A job agent run is already queued")
    return JobRunQueued(id=queued.id, run_after=queued.run_after)


__all__ = ["JobRunRequest", "job_run"]
