from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

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


__all__ = ["InboxRepository"]
