from __future__ import annotations

from datetime import timedelta
from pathlib import PurePath
from uuid import UUID, uuid4

from pydantic import ValidationError
from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from src.app.actor import set_actor, user_actor
from src.app.container import Container
from src.clients.ezcareer import RunMetadata
from src.core.exceptions import InvalidInput, ServiceException, ServiceUnavailable
from src.core.logging import get_logger
from src.db.base import utcnow
from src.features.documents import document_service
from src.features.imports.enums import ImportSource, ImportStatus
from src.features.imports.models import File, Import
from src.features.imports.schemas import ImportResumeInput, ImportResumeOutput
from src.features.profile import ProfileService, resume_profile
from src.features.profile.export import read_export
from src.features.profile.runs import run_workflow
from src.features.profile.schemas import ImportedProfile, ImportProfileInput
from src.features.settings import settings_service

logger = get_logger(__name__)

MAX_ATTEMPTS = 3
"""How many times an import is tried before it fails"""

RETRY_SECONDS = 30
"""The wait before the second attempt, doubling for each one after"""

LAPSED = "The worker stopped while reading this file"
"""The error of an import whose last attempt's worker stopped extending its lease"""


async def _read(
    file: File,
    content: bytes,
    user_id: UUID,
    metadata: RunMetadata | None,
    container: Container,
) -> ImportResumeOutput | ImportedProfile:
    """What the harness reads from the file: a résumé's draft, lines and look, or a
    profile export's profile"""
    settings = container.settings()
    ezcareer = container.ezcareer()
    if file.media_type not in settings.profile.export_types:
        return await run_workflow(
            ezcareer,
            "import-resume",
            ImportResumeOutput,
            user_id,
            ImportResumeInput(file=content),
            metadata,
        )
    read = read_export(content, settings.profile.max_unzipped_bytes)
    reply = await run_workflow(
        ezcareer,
        "import-profile",
        dict,
        user_id,
        ImportProfileInput(files=read.files),
        metadata,
    )
    try:
        imported = ImportedProfile.model_validate(reply)
    except ValidationError as error:
        raise InvalidInput(
            "import-profile replied with values ops cannot store"
        ) from error
    imported.about = imported.about.model_copy(
        update={"name": read.name, "email": read.email, "phone": read.phone}
    )
    return imported


async def _store(
    session: AsyncSession,
    row: Import,
    file: File,
    outcome: ImportResumeOutput | ImportedProfile,
    container: Container,
) -> None:
    """Write what was read onto the import: a Documents import's draft, lines and
    look, then the profile sync with its counts"""
    if isinstance(outcome, ImportResumeOutput):
        imported = resume_profile(outcome.document.content)
        if row.source is ImportSource.DOCUMENTS:
            draft = await document_service(session, container).import_draft(
                row.user_id,
                PurePath(file.filename).stem[:200] or "Résumé",
                outcome.document,
            )
            row.document_id = draft.id
            row.lines = outcome.lines
            row.suggestion = outcome.suggestion
    else:
        imported = outcome
    await ProfileService(session).sync(row, imported)


async def fail_lapsed(session: AsyncSession) -> int:
    """Fail every import whose worker stopped extending its lease on its last
    attempt, releasing its claim; how many"""
    now = utcnow()
    lapsed = (
        select(Import.id)
        .where(
            Import.status == ImportStatus.PROCESSING,
            Import.lease_until < now,
            Import.attempts >= MAX_ATTEMPTS,
        )
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    result = await session.execute(
        update(Import)
        .where(Import.id.in_(lapsed))
        .values(
            status=ImportStatus.FAILED,
            claim_token=None,
            lease_until=None,
            error=LAPSED,
            finished_at=now,
        )
    )
    return result.rowcount


async def claim_import(session: AsyncSession, lease: timedelta) -> Import | None:
    """The next import due, claimed under a fresh token and lease; None when none is
    due or another worker took the same user's Data turn first"""
    now = utcnow()
    due, other = aliased(Import), aliased(Import)
    data_turn = and_(due.source == ImportSource.DATA, due.status == ImportStatus.QUEUED)
    next_due = (
        select(due.id)
        .where(
            or_(
                and_(due.status == ImportStatus.QUEUED, due.run_after <= now),
                and_(
                    due.status == ImportStatus.PROCESSING,
                    due.lease_until < now,
                    due.attempts < MAX_ATTEMPTS,
                ),
            ),
            ~and_(
                data_turn,
                exists().where(
                    other.user_id == due.user_id,
                    other.source == ImportSource.DATA,
                    other.status == ImportStatus.PROCESSING,
                    other.lease_until >= now,
                ),
            ),
            ~and_(
                data_turn,
                exists().where(
                    other.user_id == due.user_id,
                    other.source == ImportSource.DATA,
                    other.status == ImportStatus.QUEUED,
                    other.created_at < due.created_at,
                ),
            ),
        )
        .order_by(due.run_after, due.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
        .scalar_subquery()
    )
    try:
        async with session.begin_nested():
            return await session.scalar(
                update(Import)
                .where(Import.id == next_due)
                .values(
                    status=ImportStatus.PROCESSING,
                    claim_token=uuid4(),
                    lease_until=now + lease,
                    attempts=Import.attempts + 1,
                )
                .returning(Import)
            )
    except IntegrityError:
        return None


async def heartbeat(
    session: AsyncSession, import_id: UUID, claim_token: UUID, lease: timedelta
) -> bool:
    """Extend the lease of an import still processing under the claim; False once
    the claim was lost to a newer upload or another worker"""
    result = await session.execute(
        update(Import)
        .where(
            Import.id == import_id,
            Import.claim_token == claim_token,
            Import.status == ImportStatus.PROCESSING,
        )
        .values(lease_until=utcnow() + lease)
    )
    if result.rowcount == 1:
        return True
    status = await session.scalar(
        select(Import.status).where(
            Import.id == import_id, Import.claim_token == claim_token
        )
    )
    return status is not None and status is not ImportStatus.ABANDONED


async def complete_import(
    session: AsyncSession, import_id: UUID, claim_token: UUID
) -> Import | None:
    """Mark an import still processing under the claim done and return it; None when
    the claim was lost"""
    return await session.scalar(
        update(Import)
        .where(
            Import.id == import_id,
            Import.claim_token == claim_token,
            Import.status == ImportStatus.PROCESSING,
        )
        .values(status=ImportStatus.DONE, finished_at=utcnow(), error="")
        .returning(Import)
    )


async def fail_import(
    session: AsyncSession,
    import_id: UUID,
    claim_token: UUID,
    error: str,
    *,
    retry: bool,
) -> Import | None:
    """Queue an import still processing under the claim again after a backoff when
    retry is set and attempts are left, else fail it; None when the claim was lost"""
    row = await session.scalar(
        select(Import)
        .where(
            Import.id == import_id,
            Import.claim_token == claim_token,
            Import.status == ImportStatus.PROCESSING,
        )
        .with_for_update(of=Import)
    )
    if row is None:
        return None
    row.error = error
    if retry and row.attempts < MAX_ATTEMPTS:
        row.status = ImportStatus.QUEUED
        row.run_after = utcnow() + timedelta(seconds=RETRY_SECONDS * 2**row.attempts)
    else:
        row.status = ImportStatus.FAILED
        row.finished_at = utcnow()
    await session.flush()
    return row


async def release_import(
    session: AsyncSession, import_id: UUID, claim_token: UUID
) -> bool:
    """Queue an import still processing under the claim again at once, the attempt
    uncounted; False when the claim was lost"""
    result = await session.execute(
        update(Import)
        .where(
            Import.id == import_id,
            Import.claim_token == claim_token,
            Import.status == ImportStatus.PROCESSING,
        )
        .values(
            status=ImportStatus.QUEUED,
            claim_token=None,
            lease_until=None,
            attempts=Import.attempts - 1,
        )
    )
    return result.rowcount == 1


async def _fail(
    factory: async_sessionmaker[AsyncSession],
    import_id: UUID,
    claim_token: UUID,
    error: str,
    retry: bool,
) -> None:
    """Fail the import's attempt on a session of its own"""
    async with factory() as session, session.begin():
        await fail_import(session, import_id, claim_token, error, retry=retry)


async def process_import(
    import_id: UUID, claim_token: UUID, container: Container
) -> None:
    """Read the import's file through the harness and write its results under the
    claim; a lost claim writes nothing, and a failure queues a retry or ends it"""
    factory = container.session_factory()
    async with factory() as session:
        row = await session.get(Import, import_id)
        if (
            row is None
            or row.claim_token != claim_token
            or row.status is not ImportStatus.PROCESSING
        ):
            return
        file = row.file
        metadata = await settings_service(session, container).run_metadata(row.user_id)
    set_actor(user_actor(row.user_id))
    try:
        content = await container.storage().read_private(f"{row.user_id}/{file.sha256}")
        outcome = await _read(file, content, row.user_id, metadata, container)
        async with factory() as session, session.begin():
            done = await complete_import(session, import_id, claim_token)
            if done is None:
                logger.info("import_claim_lost", import_id=str(import_id))
                return
            await _store(session, done, file, outcome, container)
    except ServiceException as error:
        logger.warning("import_failed", import_id=str(import_id), reason=error.message)
        await _fail(
            factory,
            import_id,
            claim_token,
            error.message,
            retry=isinstance(error, ServiceUnavailable),
        )
    except Exception as error:
        logger.exception("import_failed", import_id=str(import_id))
        await _fail(factory, import_id, claim_token, str(error), retry=True)


__all__ = [
    "LAPSED",
    "MAX_ATTEMPTS",
    "RETRY_SECONDS",
    "claim_import",
    "complete_import",
    "fail_import",
    "fail_lapsed",
    "heartbeat",
    "process_import",
    "release_import",
]
