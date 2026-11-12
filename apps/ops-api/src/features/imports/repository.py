from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects import postgresql, sqlite

from src.app.actor import current_actor
from src.db.base import utcnow
from src.db.repository import Repository
from src.features.imports.enums import ImportSource, ImportStatus
from src.features.imports.models import File, Import

ACTIVE = (ImportStatus.QUEUED, ImportStatus.PROCESSING)
"""The statuses of an import a worker has still to finish"""


class ImportRepository(Repository):
    async def file(
        self, user_id: UUID, sha256: str, media_type: str, size: int, filename: str
    ) -> File:
        """The user's file with this sha256, inserted the first time and named after
        the latest upload"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        upload = insert(File).values(
            user_id=user_id,
            sha256=sha256,
            media_type=media_type,
            size=size,
            filename=filename,
        )
        return await self._session.scalar(
            upload.on_conflict_do_update(
                index_elements=["user_id", "sha256"],
                set_={
                    "media_type": upload.excluded.media_type,
                    "filename": upload.excluded.filename,
                    "updated_at": utcnow(),
                    "updated_by": current_actor(),
                },
            ).returning(File)
        )

    async def latest(
        self, user_id: UUID, file_id: UUID, source: ImportSource
    ) -> Import | None:
        """The user's latest import of the file from the source, if any"""
        return await self._session.scalar(
            select(Import)
            .where(
                Import.user_id == user_id,
                Import.file_id == file_id,
                Import.source == source,
            )
            .order_by(Import.created_at.desc())
            .limit(1)
        )

    async def imports(
        self, user_id: UUID, source: ImportSource | None
    ) -> Sequence[Import]:
        """The user's imports from the source, or every source, the latest first"""
        query = select(Import).where(Import.user_id == user_id)
        if source is not None:
            query = query.where(Import.source == source)
        return (
            await self._session.scalars(query.order_by(Import.created_at.desc()))
        ).all()

    async def active(self, user_id: UUID) -> Sequence[Import]:
        """The user's queued and processing imports, the oldest first"""
        return (
            await self._session.scalars(
                select(Import)
                .where(Import.user_id == user_id, Import.status.in_(ACTIVE))
                .order_by(Import.created_at)
            )
        ).all()

    async def abandon(self, user_id: UUID, source: ImportSource) -> None:
        """Abandon the user's queued and processing imports from the source"""
        await self._session.execute(
            update(Import)
            .where(
                Import.user_id == user_id,
                Import.source == source,
                Import.status.in_(ACTIVE),
            )
            .values(status=ImportStatus.ABANDONED, finished_at=utcnow())
            .execution_options(synchronize_session="fetch")
        )

    async def queue(self, user_id: UUID, file_id: UUID, source: ImportSource) -> Import:
        """Insert a queued import of the file inside a savepoint, a Documents one
        after abandoning the user's Documents imports still queued or processing"""
        async with self._session.begin_nested():
            if source is ImportSource.DOCUMENTS:
                await self.abandon(user_id, source)
            return await self.add(
                Import(user_id=user_id, file_id=file_id, source=source)
            )

    async def flush(self) -> None:
        """Write pending changes so update timestamps are filled in"""
        await self._session.flush()


__all__ = ["ACTIVE", "ImportRepository"]
