from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects import postgresql, sqlite

from src.app.actor import current_actor
from src.db.base import utcnow
from src.db.repository import Repository
from src.features.inbox.models import EmailThread


class InboxRepository(Repository):
    async def threads(
        self, user_id: UUID, thread_ids: list[str]
    ) -> Sequence[EmailThread]:
        """The user's triaged threads among these Gmail thread ids"""
        return (
            await self._session.scalars(
                select(EmailThread).where(
                    EmailThread.user_id == user_id,
                    EmailThread.thread_id.in_(thread_ids),
                )
            )
        ).all()

    async def save(
        self, user_id: UUID, thread_id: str, **triage: object
    ) -> EmailThread:
        """Insert or update the thread's triage in one upsert, keeping its event"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        statement = insert(EmailThread).values(
            user_id=user_id, thread_id=thread_id, **triage
        )
        return await self._session.scalar(
            statement.on_conflict_do_update(
                index_elements=[EmailThread.user_id, EmailThread.thread_id],
                set_={**triage, "updated_at": utcnow(), "updated_by": current_actor()},
            ).returning(EmailThread),
            execution_options={"populate_existing": True},
        )

    async def claim_event(self, thread: EmailThread, event_id: str) -> bool:
        """Give the thread this event unless a sync already has; True if this one did"""
        return (
            await self._session.scalar(
                update(EmailThread)
                .where(EmailThread.id == thread.id, EmailThread.event_id.is_(None))
                .values(event_id=event_id)
                .returning(EmailThread.id)
            )
            is not None
        )


__all__ = ["InboxRepository"]
