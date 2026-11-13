import asyncio
from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.auth.models import User
from src.core.providers import Provider
from src.db.base import utcnow
from src.db.queue import (
    MAX_ATTEMPTS,
    RETRY_SECONDS,
    claim,
    complete,
    fail,
    fail_lapsed,
    heartbeat,
    release,
)
from src.features.connections import Connection
from src.features.jobs.enums import RunStatus, RunTrigger
from src.features.jobs.models import JobRun
from src.features.jobs.processing import JOB_RUNS, enqueue_scheduled_runs
from src.features.preferences.models import JobPreferences
from src.features.settings.models import UserSettings
from tests.conftest import PREFIX, _client
from tests.core.conftest import needs_postgres

pytestmark = needs_postgres

LEASE = timedelta(seconds=60)

JOBS = f"{PREFIX}/jobs"


async def _user(
    factory: async_sessionmaker[AsyncSession],
    zone: str | None,
    run_at: time,
    *,
    roles: str = "Backend engineer",
    jsearch: bool = True,
    disabled: bool = False,
) -> UUID:
    """A user in the zone whose daily run is due at run_at"""
    user_id = uuid4()
    async with factory() as session, session.begin():
        session.add(
            User(
                id=user_id,
                email=f"{user_id}@example.com",
                disabled_at=utcnow() if disabled else None,
            )
        )
        await session.flush()
        session.add(JobPreferences(user_id=user_id, target_roles=roles, run_at=run_at))
        session.add(UserSettings(user_id=user_id, timezone=zone))
        if jsearch:
            session.add(
                Connection(user_id=user_id, provider=Provider.JSEARCH, secret=b"key")
            )
    return user_id


async def _delete(factory: async_sessionmaker[AsyncSession], users: list[UUID]) -> None:
    """Remove the users with everything theirs"""
    async with factory() as session, session.begin():
        await session.execute(delete(User).where(User.id.in_(users)))


async def _tick(factory: async_sessionmaker[AsyncSession]) -> int:
    """One worker's tick on a session of its own"""
    async with factory() as session, session.begin():
        return await enqueue_scheduled_runs(session)


async def _runs(
    factory: async_sessionmaker[AsyncSession], user_id: UUID
) -> list[JobRun]:
    """The user's runs, the oldest first"""
    async with factory() as session:
        return list(
            (
                await session.scalars(
                    select(JobRun)
                    .where(JobRun.user_id == user_id)
                    .order_by(JobRun.created_at)
                )
            ).all()
        )


async def _claim(
    factory: async_sessionmaker[AsyncSession], lease: timedelta = LEASE
) -> JobRun | None:
    """Claim the next run due on a session of its own"""
    async with factory() as session, session.begin():
        return await claim(session, JOB_RUNS, lease)


async def _row(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> JobRun:
    """The run as the database has it now"""
    async with factory() as session:
        return await session.get_one(JobRun, run_id)


async def _due(factory: async_sessionmaker[AsyncSession], run_id: UUID) -> None:
    """Let the run be claimed now, as if its backoff had passed"""
    async with factory() as session, session.begin():
        (await session.get_one(JobRun, run_id)).run_after = utcnow() - timedelta(
            seconds=1
        )


async def _queued(postgres_app) -> UUID:
    """A manual run of the dev user, queued through the API"""
    async with _client(postgres_app) as client:
        queued = await client.post(f"{JOBS}/find")
        assert queued.status_code == 202
        return UUID(queued.json()["id"])


async def test_workers_ticking_at_once_queue_one_scheduled_run_per_user_per_day(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    users = [await _user(factory, None, time(0, 0)) for _ in range(3)]
    try:
        queued = await asyncio.gather(*(_tick(factory) for _ in range(4)))
        again = await _tick(factory)

        assert (sum(queued), again) == (3, 0)
        for user_id in users:
            [run] = await _runs(factory, user_id)
            assert (run.trigger, run.status, run.scheduled_for) == (
                RunTrigger.SCHEDULED,
                RunStatus.QUEUED,
                datetime.now(UTC).date(),
            )
            assert run.run_after <= utcnow()
    finally:
        await _delete(factory, users)


async def test_each_user_is_queued_at_their_own_local_run_at(postgres_app):
    factory = postgres_app.state.session_factory
    east = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    west = datetime.now(ZoneInfo("America/New_York"))
    kuala_lumpur = await _user(
        factory, "Asia/Kuala_Lumpur", (east - timedelta(minutes=1)).time()
    )
    new_york = await _user(
        factory, "America/New_York", (west + timedelta(minutes=1)).time()
    )
    try:
        first = await _tick(factory)
        [run] = await _runs(factory, kuala_lumpur)
        assert (first, run.scheduled_for) == (1, east.date())
        assert await _runs(factory, new_york) == []

        async with factory() as session, session.begin():
            (await session.get_one(JobPreferences, new_york)).run_at = (
                west - timedelta(minutes=1)
            ).time()
        second = await _tick(factory)

        [run] = await _runs(factory, new_york)
        assert (second, run.scheduled_for) == (1, west.date())
    finally:
        await _delete(factory, [kuala_lumpur, new_york])


async def test_no_run_for_a_disabled_user_empty_roles_or_no_jsearch_key(postgres_app):
    factory = postgres_app.state.session_factory
    users = [
        await _user(factory, "UTC", time(0, 0), disabled=True),
        await _user(factory, "UTC", time(0, 0), roles=""),
        await _user(factory, "UTC", time(0, 0), jsearch=False),
    ]
    try:
        assert await _tick(factory) == 0
        for user_id in users:
            assert await _runs(factory, user_id) == []
    finally:
        await _delete(factory, users)


async def _complete(factory: async_sessionmaker[AsyncSession], run: JobRun) -> None:
    """End the claimed run as done on a session of its own"""
    async with factory() as session, session.begin():
        await complete(session, JOB_RUNS, run.id, run.claim_token)


async def test_the_days_run_queues_while_a_find_waits_and_an_agent_run_is_for_later(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        await client.patch(
            f"{PREFIX}/preferences",
            json={"target_roles": "Backend engineer", "run_at": "00:00:00"},
        )
        await client.put(
            f"{PREFIX}/settings/connections/jsearch", json={"api_key": "rapidapi-key"}
        )
        later = (utcnow() + timedelta(hours=1)).isoformat()
        agent = await client.post(f"{JOBS}/runs", json={"run_after": later})
        manual = await client.post(f"{JOBS}/find")
        assert (agent.status_code, manual.status_code) == (202, 202)

        assert await _tick(factory) == 1

        runs = await _runs(
            factory, UUID((await client.get(f"{PREFIX}/me")).json()["id"])
        )
        assert [(run.trigger, run.status) for run in runs] == [
            (RunTrigger.AGENT, RunStatus.QUEUED),
            (RunTrigger.MANUAL, RunStatus.QUEUED),
            (RunTrigger.SCHEDULED, RunStatus.QUEUED),
        ]
        assert await _tick(factory) == 0


async def test_a_user_runs_one_run_at_a_time_in_run_after_order(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        later = (utcnow() + timedelta(hours=1)).isoformat()
        agent = UUID(
            (await client.post(f"{JOBS}/runs", json={"run_after": later})).json()["id"]
        )
        manual = UUID((await client.post(f"{JOBS}/find")).json()["id"])
        scheduled = await _user(factory, "UTC", time(0, 0))
        await _tick(factory)

        first = await _claim(factory)
        second = await _claim(factory)
        waiting = await _claim(factory)
        await _complete(factory, first)
        await _complete(factory, second)
        not_due = await _claim(factory)
        await _due(factory, agent)
        third = await _claim(factory)

        assert (first.id, first.trigger) == (manual, RunTrigger.MANUAL)
        assert (second.user_id, second.trigger) == (scheduled, RunTrigger.SCHEDULED)
        assert (waiting, not_due) == (None, None)
        assert (third.id, third.trigger) == (agent, RunTrigger.AGENT)
        await _delete(factory, [scheduled])


async def test_concurrent_claimers_never_claim_the_same_run(postgres_app):
    factory = postgres_app.state.session_factory
    users = [await _user(factory, "UTC", time(0, 0)) for _ in range(6)]
    try:
        assert await _tick(factory) == 6

        async def claim_all() -> list[UUID]:
            claimed = []
            while (row := await _claim(factory)) is not None:
                claimed.append(row.id)
                assert row.status is RunStatus.RUNNING
                assert row.claim_token is not None
            return claimed

        claimed = await asyncio.gather(*(claim_all() for _ in range(4)))
    finally:
        await _delete(factory, users)

    flat = [run_id for worker in claimed for run_id in worker]
    assert len(flat) == len(set(flat)) == 6


async def test_a_lapsed_lease_lets_another_worker_reclaim_a_run_and_fences_the_first_out(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    run_id = await _queued(postgres_app)
    first = await _claim(factory, timedelta(0))

    second = await _claim(factory)

    assert (first.id, second.id) == (run_id, run_id)
    assert second.claim_token != first.claim_token
    assert second.attempts == 2
    async with factory() as session, session.begin():
        assert (
            await heartbeat(session, JOB_RUNS, run_id, first.claim_token, LEASE)
            is False
        )
        assert await complete(session, JOB_RUNS, run_id, first.claim_token) is None
        assert (
            await heartbeat(session, JOB_RUNS, run_id, second.claim_token, LEASE)
            is True
        )
        done = await complete(session, JOB_RUNS, run_id, second.claim_token)
        assert done.status is RunStatus.DONE
    row = await _row(factory, run_id)
    assert row.status is RunStatus.DONE
    assert row.finished_at is not None


async def test_a_failed_run_waits_longer_each_time_until_the_last(postgres_app):
    factory = postgres_app.state.session_factory
    run_id = await _queued(postgres_app)
    waits = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        claimed = await _claim(factory)
        assert (claimed.id, claimed.attempts) == (run_id, attempt)
        async with factory() as session, session.begin():
            failed = await fail(
                session,
                JOB_RUNS,
                run_id,
                claimed.claim_token,
                f"attempt {attempt}",
                retry=True,
            )
            waits.append((failed.status, failed.run_after - utcnow()))
        assert await _claim(factory) is None
        await _due(factory, run_id)

    assert [status for status, _ in waits] == [
        RunStatus.QUEUED,
        RunStatus.QUEUED,
        RunStatus.FAILED,
    ]
    assert [round(wait.total_seconds(), -1) for _, wait in waits[:2]] == [
        RETRY_SECONDS * 2,
        RETRY_SECONDS * 4,
    ]
    row = await _row(factory, run_id)
    assert (row.error, row.attempts) == ("attempt 3", MAX_ATTEMPTS)
    assert row.finished_at is not None
    assert await _claim(factory) is None


async def test_a_worker_that_keeps_dying_fails_the_run_after_its_last_attempt(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    run_id = await _queued(postgres_app)

    attempts = []
    for _ in range(MAX_ATTEMPTS + 2):
        claimed = await _claim(factory, timedelta(0))
        attempts.append(None if claimed is None else claimed.attempts)
    async with factory() as session, session.begin():
        failed = await fail_lapsed(session, JOB_RUNS)

    assert attempts == [1, 2, 3, None, None]
    assert failed == 1
    async with _client(postgres_app) as client:
        latest = (await client.get(f"{JOBS}/runs/latest")).json()
    assert (latest["status"], latest["error"]) == ("failed", JOB_RUNS.lapsed)
    row = await _row(factory, run_id)
    assert (row.claim_token, row.lease_until) == (None, None)
    assert await _claim(factory) is None


async def test_a_released_run_is_queued_again_with_its_attempt_uncounted(postgres_app):
    factory = postgres_app.state.session_factory
    run_id = await _queued(postgres_app)
    claimed = await _claim(factory)

    async with factory() as session, session.begin():
        released = await release(session, JOB_RUNS, run_id, claimed.claim_token)
        again = await release(session, JOB_RUNS, run_id, claimed.claim_token)

    assert (released, again) == (True, False)
    row = await _row(factory, run_id)
    assert (row.status, row.attempts) == (RunStatus.QUEUED, 0)
    assert (row.claim_token, row.lease_until) == (None, None)
    assert (await _claim(factory)).attempts == 1
