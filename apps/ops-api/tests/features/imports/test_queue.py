import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.auth.models import User
from src.db.base import utcnow
from src.features.imports.enums import ImportSource, ImportStatus
from src.features.imports.models import File, Import
from src.features.imports.processing import (
    LAPSED,
    MAX_ATTEMPTS,
    RETRY_SECONDS,
    claim_import,
    complete_import,
    fail_import,
    fail_lapsed,
    heartbeat,
    release_import,
)
from src.features.profile.enums import EntryKind
from src.features.profile.models import ProfileEntry, ProfileSkill
from src.features.profile.schemas import ImportedEntry, ImportedProfile, ImportedSkill
from src.features.profile.service import ProfileService
from tests.conftest import PREFIX, _client
from tests.core.conftest import needs_postgres

pytestmark = needs_postgres

LEASE = timedelta(seconds=60)

PDF = b"%PDF-1.7 resume"


async def _queued(
    factory: async_sessionmaker[AsyncSession],
    user_id: UUID,
    source: ImportSource,
    count: int = 1,
) -> list[UUID]:
    """Queue count imports of new files for the user, the first the oldest"""
    ids = []
    async with factory() as session, session.begin():
        for number in range(count):
            file = File(
                user_id=user_id,
                sha256=uuid4().hex + uuid4().hex,
                media_type="application/pdf",
                size=1,
                filename=f"{number}.pdf",
            )
            session.add(file)
            await session.flush()
            row = Import(user_id=user_id, file_id=file.id, source=source)
            session.add(row)
            await session.flush()
            ids.append(row.id)
    return ids


async def _claim(
    factory: async_sessionmaker[AsyncSession], lease: timedelta = LEASE
) -> Import | None:
    """Claim the next import due on a session of its own"""
    async with factory() as session, session.begin():
        return await claim_import(session, lease)


async def _row(factory: async_sessionmaker[AsyncSession], import_id: UUID) -> Import:
    """The import as the database has it now"""
    async with factory() as session:
        return await session.get_one(Import, import_id)


async def _due(factory: async_sessionmaker[AsyncSession], import_id: UUID) -> None:
    """Let the import be claimed now, as if its backoff had passed"""
    async with factory() as session, session.begin():
        (await session.get_one(Import, import_id)).run_after = utcnow() - timedelta(
            seconds=1
        )


async def test_concurrent_claimers_never_claim_the_same_import(postgres_app):
    factory = postgres_app.state.session_factory
    users = [User(id=uuid4(), email=f"{uuid4()}@example.com") for _ in range(6)]
    async with factory() as session, session.begin():
        session.add_all(users)
    try:
        queued = [
            (await _queued(factory, user.id, ImportSource.DOCUMENTS))[0]
            for user in users
        ]

        async def claim_all() -> list[UUID]:
            claimed = []
            while (row := await _claim(factory)) is not None:
                claimed.append(row.id)
                assert row.status is ImportStatus.PROCESSING
                assert row.claim_token is not None
            return claimed

        claimed = await asyncio.gather(*(claim_all() for _ in range(4)))
    finally:
        async with factory() as session, session.begin():
            await session.execute(
                delete(User).where(User.id.in_([user.id for user in users]))
            )

    flat = [import_id for worker in claimed for import_id in worker]
    assert len(flat) == len(set(flat))
    assert set(queued) <= set(flat)


async def test_a_users_data_imports_run_oldest_first_one_at_a_time(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    first, second, third = await _queued(factory, user_id, ImportSource.DATA, 3)

    claimed = await _claim(factory)
    waiting = await _claim(factory)

    assert (claimed.id, waiting) == (first, None)
    async with factory() as session, session.begin():
        await complete_import(session, first, claimed.claim_token)
    claimed = await _claim(factory)
    assert claimed.id == second
    async with factory() as session, session.begin():
        await fail_import(
            session, second, claimed.claim_token, "harness away", retry=True
        )
    assert await _claim(factory) is None
    await _due(factory, second)
    assert (await _claim(factory)).id == second
    assert await _claim(factory) is None
    assert (await _row(factory, third)).status is ImportStatus.QUEUED


async def test_a_data_turn_lost_to_another_worker_claims_nothing(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    first, second = await _queued(factory, user_id, ImportSource.DATA, 2)
    lapsed = await _claim(factory, timedelta(0))
    assert lapsed.id == first

    async with factory() as one, one.begin():
        reclaimed = await claim_import(one, LEASE)
        other = asyncio.create_task(_claim(factory))
        await asyncio.sleep(0.3)
        assert not other.done()
    assert await other is None

    assert reclaimed.id == first
    assert reclaimed.claim_token != lapsed.claim_token
    assert (await _row(factory, second)).status is ImportStatus.QUEUED


async def test_a_newer_documents_upload_abandons_and_fences_out_the_one_processing(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        first = await client.post(
            f"{PREFIX}/documents/imports",
            files={"file": ("one.pdf", PDF, "application/pdf")},
        )
        claimed = await _claim(factory)
        assert claimed.id == UUID(first.json()["id"])

        second = await client.post(
            f"{PREFIX}/documents/imports",
            files={"file": ("two.pdf", PDF + b"2", "application/pdf")},
        )
        async with factory() as session, session.begin():
            extended = await heartbeat(session, claimed.id, claimed.claim_token, LEASE)
            completed = await complete_import(session, claimed.id, claimed.claim_token)

        assert (extended, completed) == (False, None)
        listed = {
            i["id"]: i for i in (await client.get(f"{PREFIX}/documents/imports")).json()
        }
        assert listed[first.json()["id"]]["status"] == "abandoned"
        assert listed[second.json()["id"]]["status"] == "queued"
        assert (await _claim(factory)).id == UUID(second.json()["id"])


async def test_a_lapsed_lease_lets_another_worker_reclaim_and_fences_the_first_out(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    [import_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)
    first = await _claim(factory, timedelta(0))

    second = await _claim(factory)

    assert (first.id, second.id) == (import_id, import_id)
    assert second.claim_token != first.claim_token
    assert second.attempts == 2
    async with factory() as session, session.begin():
        assert await heartbeat(session, import_id, first.claim_token, LEASE) is False
        assert await complete_import(session, import_id, first.claim_token) is None
        assert await heartbeat(session, import_id, second.claim_token, LEASE) is True
        done = await complete_import(session, import_id, second.claim_token)
        assert done.status is ImportStatus.DONE
    row = await _row(factory, import_id)
    assert row.status is ImportStatus.DONE
    assert row.finished_at is not None


async def test_a_failed_attempt_waits_longer_each_time_until_the_last(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    [import_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)
    waits = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        claimed = await _claim(factory)
        assert (claimed.id, claimed.attempts) == (import_id, attempt)
        async with factory() as session, session.begin():
            failed = await fail_import(
                session,
                import_id,
                claimed.claim_token,
                f"attempt {attempt}",
                retry=True,
            )
            waits.append((failed.status, failed.run_after - utcnow()))
        assert await _claim(factory) is None
        await _due(factory, import_id)

    assert [status for status, _ in waits] == [
        ImportStatus.QUEUED,
        ImportStatus.QUEUED,
        ImportStatus.FAILED,
    ]
    assert [round(wait.total_seconds(), -1) for _, wait in waits[:2]] == [
        RETRY_SECONDS * 2,
        RETRY_SECONDS * 4,
    ]
    row = await _row(factory, import_id)
    assert (row.error, row.attempts) == ("attempt 3", MAX_ATTEMPTS)
    assert row.finished_at is not None
    assert await _claim(factory) is None


async def test_a_worker_that_keeps_dying_fails_the_import_after_its_last_attempt(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    [import_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)

    attempts = []
    for _ in range(MAX_ATTEMPTS + 2):
        claimed = await _claim(factory, timedelta(0))
        attempts.append(None if claimed is None else claimed.attempts)
    async with factory() as session, session.begin():
        failed = await fail_lapsed(session)

    assert attempts == [1, 2, 3, None, None]
    assert failed == 1
    row = await _row(factory, import_id)
    assert (row.status, row.attempts, row.error) == (ImportStatus.FAILED, 3, LAPSED)
    assert (row.claim_token, row.lease_until) == (None, None)
    assert row.finished_at is not None
    assert await _claim(factory) is None


async def test_a_last_attempt_still_under_lease_is_left_to_its_worker(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    [import_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)
    for _ in range(MAX_ATTEMPTS - 1):
        await _claim(factory, timedelta(0))
    last = await _claim(factory)

    async with factory() as session, session.begin():
        failed = await fail_lapsed(session)

    assert (last.attempts, failed) == (MAX_ATTEMPTS, 0)
    assert (await _row(factory, import_id)).status is ImportStatus.PROCESSING
    async with factory() as session, session.begin():
        assert await heartbeat(session, import_id, last.claim_token, LEASE) is True


async def test_a_released_import_is_queued_again_with_its_attempt_uncounted(
    postgres_app,
):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
    [import_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)
    claimed = await _claim(factory)

    async with factory() as session, session.begin():
        released = await release_import(session, import_id, claimed.claim_token)
        again = await release_import(session, import_id, claimed.claim_token)

    assert (released, again) == (True, False)
    row = await _row(factory, import_id)
    assert (row.status, row.attempts) == (ImportStatus.QUEUED, 0)
    assert (row.claim_token, row.lease_until) == (None, None)
    async with factory() as session, session.begin():
        assert await heartbeat(session, import_id, claimed.claim_token, LEASE) is False
    assert (await _claim(factory)).attempts == 1


async def test_two_workers_syncing_one_users_profile_add_its_facts_once(postgres_app):
    factory = postgres_app.state.session_factory
    async with _client(postgres_app) as client:
        user_id = UUID((await client.get(f"{PREFIX}/me")).json()["id"])
        await client.patch(f"{PREFIX}/profile", json={"headline": "x"})
    [data_id] = await _queued(factory, user_id, ImportSource.DATA)
    [documents_id] = await _queued(factory, user_id, ImportSource.DOCUMENTS)
    imported = ImportedProfile(
        entries=[
            ImportedEntry(
                kind=EntryKind.ROLE,
                title="Engineer",
                organisation="Acme",
                start="2020-01",
            )
        ],
        skills=[ImportedSkill(name="Python")],
    )
    gate = asyncio.Event()

    async def finish(claimed: Import) -> None:
        async with factory() as session, session.begin():
            done = await complete_import(session, claimed.id, claimed.claim_token)
            await ProfileService(session).sync(done, imported)
            await gate.wait()

    first = asyncio.create_task(finish(await _claim(factory)))
    second = asyncio.create_task(finish(await _claim(factory)))
    await asyncio.sleep(0.5)
    gate.set()
    await asyncio.gather(first, second)

    async with factory() as session:
        entries = await session.scalar(
            select(func.count()).where(ProfileEntry.user_id == user_id)
        )
        skills = await session.scalar(
            select(func.count()).where(ProfileSkill.user_id == user_id)
        )
    assert (entries, skills) == (1, 1)
    rows = [await _row(factory, data_id), await _row(factory, documents_id)]
    assert sorted((row.added, row.matched) for row in rows) == [(0, 2), (2, 0)]


async def test_two_documents_uploads_at_once_both_queue_and_the_later_one_stays(
    postgres_app,
):
    async with _client(postgres_app) as client:
        await client.get(f"{PREFIX}/me")
        for attempt in range(8):
            responses = await asyncio.gather(
                client.post(
                    f"{PREFIX}/documents/imports",
                    files={
                        "file": (
                            f"a{attempt}.pdf",
                            PDF + b"a%d" % attempt,
                            "application/pdf",
                        )
                    },
                ),
                client.post(
                    f"{PREFIX}/documents/imports",
                    files={
                        "file": (
                            f"b{attempt}.pdf",
                            PDF + b"b%d" % attempt,
                            "application/pdf",
                        )
                    },
                ),
            )
            assert [r.status_code for r in responses] == [201, 201]
            active = (await client.get(f"{PREFIX}/imports/active")).json()
            assert [a["id"] for a in active] == [
                max(responses, key=lambda r: r.json()["created_at"]).json()["id"]
            ]
