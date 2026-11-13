from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ColumnElement, and_, exists, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from src.app.actor import set_actor, user_actor
from src.app.container import Container
from src.core.exceptions import ServiceException, ServiceUnavailable
from src.core.logging import get_logger
from src.core.providers import Provider
from src.db.queue import Queue, complete, fail
from src.features.jobs.enums import RunStatus
from src.features.jobs.models import JobRun
from src.features.jobs.router import job_service
from src.features.jobs.schemas import FindJobsInput, FindJobsOutput
from src.features.jobs.tools.job_search import source_key
from src.features.profile import ProfileService
from src.features.settings import settings_service

logger = get_logger(__name__)


def _user_turn(due: type[JobRun], now: datetime) -> ColumnElement[bool]:
    """Whether a due run may be claimed: a queued run waits while a worker runs
    another of the user's"""
    other = aliased(JobRun)
    return ~and_(
        due.status == RunStatus.QUEUED,
        exists().where(other.user_id == due.user_id, other.status == RunStatus.RUNNING),
    )


JOB_RUNS = Queue(
    model=JobRun,
    queued=RunStatus.QUEUED,
    running=RunStatus.RUNNING,
    done=RunStatus.DONE,
    failed=RunStatus.FAILED,
    lapsed="The worker stopped while searching for jobs",
    eligible=_user_turn,
)
"""The job runs a worker claims, one per user at a time"""

ENQUEUE_SCHEDULED = text("""
    INSERT INTO job_runs
        (id, user_id, trigger, scheduled_for, status, attempts, error, found, new, matched)
    SELECT gen_random_uuid(), u.id, 'scheduled',
        (now() AT TIME ZONE coalesce(s.timezone, 'UTC'))::date, 'queued', 0, '', 0, 0, 0
    FROM users u
    JOIN job_preferences p ON p.user_id = u.id
    LEFT JOIN user_settings s ON s.user_id = u.id
    WHERE u.disabled_at IS NULL
        AND p.target_roles <> ''
        AND EXISTS (
            SELECT 1 FROM connections c WHERE c.user_id = u.id AND c.provider = :provider
        )
        AND (now() AT TIME ZONE coalesce(s.timezone, 'UTC'))::time >= p.run_at
    ON CONFLICT DO NOTHING
""")
"""Queue today's scheduled run for every enabled user with target roles, a connection
to the provider and a local time past run_at, unless the day's run exists"""


async def enqueue_scheduled_runs(session: AsyncSession, provider: Provider) -> int:
    """Queue the scheduled runs due today in the users' own time zones for users
    connected to the provider; how many"""
    return (await session.execute(ENQUEUE_SCHEDULED, {"provider": provider})).rowcount


async def _fail(
    factory: async_sessionmaker[AsyncSession],
    run_id: UUID,
    claim_token: UUID,
    error: str,
    retry: bool,
) -> None:
    """Fail the run's attempt on a session of its own"""
    async with factory() as session, session.begin():
        await fail(session, JOB_RUNS, run_id, claim_token, error, retry=retry)


async def process_job_run(
    run_id: UUID, claim_token: UUID, container: Container
) -> None:
    """Run find-jobs on the profile and the run's search and store what it found
    under the claim; a lost claim writes nothing, a failure queues a retry or ends it"""
    factory = container.session_factory()
    try:
        async with factory() as session:
            row = await session.get(JobRun, run_id)
            if (
                row is None
                or row.claim_token != claim_token
                or row.status is not RunStatus.RUNNING
            ):
                return
            set_actor(user_actor(row.user_id))
            await source_key(session, container.job_source(), row.user_id)
            profile = await ProfileService(session).agent_profile(row.user_id)
            metadata = await settings_service(session, container).run_metadata(
                row.user_id
            )
        reply = await container.runner().run(
            row.user_id,
            "find-jobs",
            FindJobsOutput,
            data=FindJobsInput(
                facts=profile.facts, preferences=profile.preferences, search=row.search
            ),
            metadata=metadata,
        )
        async with factory() as session, session.begin():
            done = await complete(session, JOB_RUNS, run_id, claim_token)
            if done is None:
                logger.info("job_run_claim_lost", run_id=str(run_id))
                return
            await job_service(session, container).keep_found(
                done, reply, container.job_source().label
            )
    except ServiceException as error:
        logger.warning("job_run_failed", run_id=str(run_id), reason=error.message)
        await _fail(
            factory,
            run_id,
            claim_token,
            error.message,
            retry=isinstance(error, ServiceUnavailable),
        )
    except Exception as error:
        logger.exception("job_run_failed", run_id=str(run_id))
        await _fail(factory, run_id, claim_token, str(error), retry=True)


__all__ = ["JOB_RUNS", "enqueue_scheduled_runs", "process_job_run"]
