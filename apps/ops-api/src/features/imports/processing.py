from __future__ import annotations

from datetime import datetime
from pathlib import PurePath
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import ColumnElement, and_, exists
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import aliased

from src.app.actor import set_actor, user_actor
from src.app.container import Container
from src.clients.ezcareer import RunMetadata
from src.core.exceptions import InvalidInput, ServiceException, ServiceUnavailable
from src.core.logging import get_logger
from src.db.queue import Queue, complete, fail
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


def _data_turn(due: type[Import], now: datetime) -> ColumnElement[bool]:
    """Whether a due import may be claimed: a queued Data import waits while the same
    user has another Data import processing under a live lease or an older one queued"""
    other = aliased(Import)
    data_turn = and_(due.source == ImportSource.DATA, due.status == ImportStatus.QUEUED)
    return and_(
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


IMPORTS = Queue(
    model=Import,
    queued=ImportStatus.QUEUED,
    running=ImportStatus.PROCESSING,
    done=ImportStatus.DONE,
    failed=ImportStatus.FAILED,
    lapsed="The worker stopped while reading this file",
    abandoned=ImportStatus.ABANDONED,
    eligible=_data_turn,
)
"""The imports a worker claims, one Data import per user at a time"""


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


async def _fail(
    factory: async_sessionmaker[AsyncSession],
    import_id: UUID,
    claim_token: UUID,
    error: str,
    retry: bool,
) -> None:
    """Fail the import's attempt on a session of its own"""
    async with factory() as session, session.begin():
        await fail(session, IMPORTS, import_id, claim_token, error, retry=retry)


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
            done = await complete(session, IMPORTS, import_id, claim_token)
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


__all__ = ["IMPORTS", "process_import"]
