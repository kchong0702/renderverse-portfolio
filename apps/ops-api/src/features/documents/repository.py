from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from document_schema import DocumentKind
from sqlalchemy import and_, func, or_, select, update

from src.db.repository import Repository
from src.features.documents.enums import ImportStatus
from src.features.documents.models import (
    Document,
    DocumentChangeset,
    DocumentImport,
    DocumentVersion,
)


class DocumentRepository(Repository):
    async def documents(self, user_id: UUID) -> Sequence[Document]:
        """The user's documents, masters first, then the latest changed"""
        return (
            await self._session.scalars(
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.master.desc(), Document.updated_at.desc())
            )
        ).all()

    async def clear_master(self, user_id: UUID, kind: DocumentKind) -> None:
        """Unmark the user's master document of this kind, if there is one"""
        await self._session.execute(
            update(Document)
            .where(Document.user_id == user_id, Document.kind == kind)
            .values(master=False)
            .execution_options(synchronize_session="fetch")
        )

    async def versions(self, document_id: UUID) -> Sequence[DocumentVersion]:
        """A document's versions, the latest first"""
        return (
            await self._session.scalars(
                select(DocumentVersion)
                .where(DocumentVersion.document_id == document_id)
                .order_by(DocumentVersion.number.desc())
            )
        ).all()

    async def version(
        self, document_id: UUID, version_id: UUID
    ) -> DocumentVersion | None:
        """One of the document's versions, or None when it is another's"""
        version = await self._session.get(DocumentVersion, version_id)
        return version if version and version.document_id == document_id else None

    async def last_version_number(self, document_id: UUID) -> int:
        """The highest version number of a document; 0 before its first"""
        return (
            await self._session.scalar(
                select(func.max(DocumentVersion.number)).where(
                    DocumentVersion.document_id == document_id
                )
            )
        ) or 0

    async def changesets(
        self, document_ids: Sequence[UUID]
    ) -> Sequence[DocumentChangeset]:
        """The changesets for these documents, the latest first"""
        return (
            await self._session.scalars(
                select(DocumentChangeset)
                .where(DocumentChangeset.document_id.in_(document_ids))
                .order_by(DocumentChangeset.created_at.desc())
            )
        ).all()

    async def changeset(
        self, document_id: UUID, changeset_id: UUID
    ) -> DocumentChangeset | None:
        """One of the document's changesets, or None when it is another's"""
        changeset = await self._session.get(DocumentChangeset, changeset_id)
        return changeset if changeset and changeset.document_id == document_id else None

    async def imports(self, user_id: UUID) -> Sequence[DocumentImport]:
        """The user's imports, the latest first"""
        return (
            await self._session.scalars(
                select(DocumentImport)
                .where(DocumentImport.user_id == user_id)
                .order_by(DocumentImport.created_at.desc())
            )
        ).all()

    async def claim_import(
        self, user_id: UUID, import_id: UUID, stale_before: datetime
    ) -> DocumentImport | None:
        """Mark the user's import running unless it is done or a read claimed it after
        stale_before; None when there is no such import to claim"""
        return await self._session.scalar(
            update(DocumentImport)
            .where(
                DocumentImport.id == import_id,
                DocumentImport.user_id == user_id,
                or_(
                    DocumentImport.status.in_(
                        [ImportStatus.PENDING, ImportStatus.FAILED]
                    ),
                    and_(
                        DocumentImport.status == ImportStatus.RUNNING,
                        DocumentImport.updated_at < stale_before,
                    ),
                ),
            )
            .values(status=ImportStatus.RUNNING)
            .returning(DocumentImport)
        )

    async def file(self, row: DocumentImport) -> bytes:
        """The import's uploaded file, which loads only when asked for"""
        await self._session.refresh(row, ["content"])
        return row.content

    async def flush(self) -> None:
        """Write pending changes so update timestamps are filled in"""
        await self._session.flush()


__all__ = ["DocumentRepository"]
