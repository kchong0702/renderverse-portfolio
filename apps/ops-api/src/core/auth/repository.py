from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, delete, select
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.models import AuthIdentity, AuthSession, SignInAttempts, User


class AuthRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def user(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)

    async def user_by_email(self, email: str) -> User | None:
        return await self._session.scalar(select(User).where(User.email == email))

    async def identity(self, provider: str, subject: str) -> AuthIdentity | None:
        return await self._session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.provider == provider, AuthIdentity.subject == subject
            )
        )

    async def live_session(self, token_hash: str, now: datetime) -> AuthSession | None:
        return await self._session.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_hash, AuthSession.expires_at > now
            )
        )

    async def delete_session(self, token_hash: str) -> None:
        await self._session.execute(
            delete(AuthSession).where(AuthSession.token_hash == token_hash)
        )

    async def delete_expired_sessions(self, user_id: UUID, now: datetime) -> None:
        await self._session.execute(
            delete(AuthSession).where(
                AuthSession.user_id == user_id, AuthSession.expires_at <= now
            )
        )

    async def count_sign_in_attempt(
        self, email: str, now: datetime, window_ends_at: datetime
    ) -> int:
        """Count one more attempt for the email and return its total in the window.

        One upsert, so parallel requests each get their own count and a burst cannot
        slip past the limit; a window that has ended starts again at 1."""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        ended = SignInAttempts.window_ends_at <= now
        statement = insert(SignInAttempts).values(
            email=email, attempts=1, window_ends_at=window_ends_at
        )
        statement = statement.on_conflict_do_update(
            index_elements=[SignInAttempts.email],
            set_={
                "attempts": case((ended, 1), else_=SignInAttempts.attempts + 1),
                "window_ends_at": case(
                    (ended, statement.excluded.window_ends_at),
                    else_=SignInAttempts.window_ends_at,
                ),
            },
        )
        return (
            await self._session.scalar(statement.returning(SignInAttempts.attempts))
            or 0
        )

    async def clear_sign_in_attempts(self, email: str) -> None:
        await self._session.execute(
            delete(SignInAttempts).where(SignInAttempts.email == email)
        )

    async def delete_ended_sign_in_windows(self, now: datetime) -> None:
        await self._session.execute(
            delete(SignInAttempts).where(SignInAttempts.window_ends_at <= now)
        )

    async def commit(self) -> None:
        await self._session.commit()

    async def add(self, row: User | AuthIdentity | AuthSession) -> None:
        self._session.add(row)
        await self._session.flush()


__all__ = ["AuthRepository"]
