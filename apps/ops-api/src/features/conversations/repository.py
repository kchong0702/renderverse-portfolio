from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError

from src.db.base import utcnow
from src.db.repository import Repository
from src.features.conversations.enums import ServedAgent
from src.features.conversations.models import AgentSession, AgentThread, ThreadMessage


class ConversationRepository(Repository):
    async def open_sessions(self, user_id: UUID) -> None:
        """Make each served agent's session for the user if the user has none yet,
        career-director's with its first thread"""
        opened = set(
            await self._session.scalars(
                select(AgentSession.agent).where(AgentSession.user_id == user_id)
            )
        )
        for agent in ServedAgent:
            if agent in opened:
                continue
            if agent is ServedAgent.CAREER_CONSULTANT:
                await self.add(AgentSession(user_id=user_id, agent=agent))
                continue
            thread_id = uuid4()
            session = await self.add(
                AgentSession(user_id=user_id, agent=agent, active_thread_id=thread_id)
            )
            await self.add(
                AgentThread(id=thread_id, user_id=user_id, session_id=session.id)
            )

    async def session(self, user_id: UUID, agent: ServedAgent) -> AgentSession | None:
        """The user's session with the agent, or None before sign-in made it"""
        return await self._session.scalar(
            select(AgentSession).where(
                AgentSession.user_id == user_id, AgentSession.agent == agent
            )
        )

    async def document_thread(
        self, session: AgentSession, document_id: UUID
    ) -> AgentThread:
        """The session's active thread on the document, made the first time"""
        query = select(AgentThread).where(
            AgentThread.session_id == session.id,
            AgentThread.document_id == document_id,
            AgentThread.cleared_at.is_(None),
        )
        if thread := await self._session.scalar(query):
            return thread
        try:
            async with self._session.begin_nested():
                return await self.add(
                    AgentThread(
                        user_id=session.user_id,
                        session_id=session.id,
                        document_id=document_id,
                    )
                )
        except IntegrityError:
            return (await self._session.scalars(query)).one()

    async def replace(self, thread_id: UUID) -> AgentThread:
        """Mark the thread cleared and add the one new turns go on in its place, or
        return that one when a clear running at once already did"""
        thread = await self._session.get_one(
            AgentThread, thread_id, with_for_update=True, populate_existing=True
        )
        if thread.cleared_at:
            return (
                await self._session.scalars(
                    select(AgentThread).where(
                        AgentThread.session_id == thread.session_id,
                        AgentThread.document_id.is_not_distinct_from(
                            thread.document_id
                        ),
                        AgentThread.cleared_at.is_(None),
                    )
                )
            ).one()
        thread.cleared_at = utcnow()
        await self._session.flush()
        return await self.add(
            AgentThread(
                user_id=thread.user_id,
                session_id=thread.session_id,
                document_id=thread.document_id,
            )
        )

    async def thread(
        self, user_id: UUID, thread_id: UUID
    ) -> tuple[ServedAgent, UUID | None, bool] | None:
        """The agent of the session the user's thread belongs to, the thread's document
        and whether it was cleared; None when the thread is missing or another user's"""
        row = (
            await self._session.execute(
                select(
                    AgentSession.agent, AgentThread.document_id, AgentThread.cleared_at
                )
                .join(AgentThread, AgentThread.session_id == AgentSession.id)
                .where(AgentThread.id == thread_id, AgentThread.user_id == user_id)
            )
        ).one_or_none()
        return (row.agent, row.document_id, row.cleared_at is not None) if row else None

    async def page(
        self, thread_id: UUID, before: ThreadMessage | None, limit: int
    ) -> Sequence[ThreadMessage]:
        """Up to limit of the thread's messages before the message `before`, or its
        latest, the newest first"""
        query = select(ThreadMessage).where(ThreadMessage.thread_id == thread_id)
        if before:
            query = query.where(
                tuple_(ThreadMessage.created_at, ThreadMessage.id)
                < tuple_(before.created_at, before.id)
            )
        return (
            await self._session.scalars(
                query.order_by(
                    ThreadMessage.created_at.desc(), ThreadMessage.id.desc()
                ).limit(limit)
            )
        ).all()

    async def message(self, thread_id: UUID, message_id: str) -> ThreadMessage | None:
        """One of the thread's messages, or None when it is missing or another
        thread's"""
        message = await self._session.get(ThreadMessage, message_id)
        return message if message and message.thread_id == thread_id else None


__all__ = ["ConversationRepository"]
