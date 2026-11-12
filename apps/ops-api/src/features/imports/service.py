from __future__ import annotations

from hashlib import sha256
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.storage import Storage
from src.core.config import DocumentsSettings, ProfileSettings
from src.core.exceptions import Conflict, InvalidInput, NotFound
from src.db.base import utcnow
from src.features.imports.enums import ImportSource, ImportStatus
from src.features.imports.models import File, Import
from src.features.imports.repository import ACTIVE, ImportRepository
from src.features.imports.schemas import ImportRead


def _read(row: Import, file: File) -> ImportRead:
    """The import with its file as the API returns it"""
    return ImportRead(
        id=row.id,
        source=row.source,
        filename=file.filename,
        media_type=file.media_type,
        size=file.size,
        status=row.status,
        document_id=row.document_id,
        suggestion=row.suggestion,
        added=row.added,
        conflicts=row.conflicts,
        matched=row.matched,
        error=row.error,
        created_at=row.created_at,
        finished_at=row.finished_at,
    )


class ImportService:
    def __init__(
        self,
        session: AsyncSession,
        storage: Storage,
        documents: DocumentsSettings,
        profile: ProfileSettings,
    ):
        """Keep files in private storage and imports through a repository on the
        session, within the documents and profile upload limits"""
        self._repository = ImportRepository(session)
        self._storage = storage
        self._documents = documents
        self._profile = profile

    async def imports(
        self, user_id: UUID, source: ImportSource | None = None
    ) -> list[ImportRead]:
        """The user's imports from the source, or every source, the latest first"""
        return [
            _read(row, row.file)
            for row in await self._repository.imports(user_id, source)
        ]

    async def active(self, user_id: UUID) -> list[ImportRead]:
        """The user's queued and processing imports, the oldest first"""
        return [_read(row, row.file) for row in await self._repository.active(user_id)]

    async def upload(
        self,
        user_id: UUID,
        source: ImportSource,
        filename: str,
        media_type: str,
        content: bytes,
    ) -> ImportRead:
        """Store the file and queue an import of it, abandoning the user's earlier
        Documents import for a Documents upload; a Data file already imported is
        returned as it is"""
        export = (
            source is ImportSource.DATA and media_type in self._profile.export_types
        )
        if not export and media_type not in self._documents.upload_types:
            raise InvalidInput(
                "Upload a PDF, Word (.docx) or .zip file"
                if source is ImportSource.DATA
                else "Upload a PDF or Word (.docx) file"
            )
        limit = (
            self._profile.max_export_bytes
            if export
            else self._documents.max_upload_bytes
        )
        if not content or len(content) > limit:
            raise InvalidInput(
                f"The file must be between 1 byte and {limit // (1024 * 1024)} MB"
            )
        digest = sha256(content).hexdigest()
        await self._storage.put_private(f"{user_id}/{digest}", content, media_type)
        file = await self._repository.file(
            user_id, digest, media_type, len(content), filename[:255]
        )
        if source is ImportSource.DATA:
            last = await self._repository.latest(user_id, file.id, source)
            if last is not None and last.status is ImportStatus.DONE:
                return _read(last, file)
        try:
            row = await self._repository.queue(user_id, file.id, source)
        except IntegrityError:
            try:
                row = await self._repository.queue(user_id, file.id, source)
            except IntegrityError as error:
                raise Conflict("Another résumé is being imported; try again") from error
        return _read(row, file)

    async def delete(self, user_id: UUID, import_id: UUID) -> None:
        """Abandon an import still queued or processing; Conflict for a finished one"""
        row = await self._repository.owned(Import, user_id, import_id)
        if row is None:
            raise NotFound("No such import")
        if row.status not in ACTIVE:
            raise Conflict("This import is finished and stays in the history")
        row.status = ImportStatus.ABANDONED
        row.finished_at = utcnow()
        await self._repository.flush()


__all__ = ["ImportService"]
