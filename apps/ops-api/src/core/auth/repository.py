from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, delete, exists, select
from sqlalchemy.dialects import postgresql, sqlite

from src.core.auth.enums import AttemptScope, IdentityProvider
from src.core.auth.models import AuthIdentity, AuthSession, SignInAttempts, User
from src.db.repository import Repository


class AuthRepository(Repository):
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

    async def identities(self, user_id: UUID) -> list[AuthIdentity]:
        """Every way the user signs in"""
        return list(
            await self._session.scalars(
                select(AuthIdentity).where(AuthIdentity.user_id == user_id)
            )
        )

    async def user_identity(
        self, user_id: UUID, provider: IdentityProvider
    ) -> AuthIdentity | None:
        """The user's identity with this provider, if they have one"""
        return await self._session.scalar(
            select(AuthIdentity).where(
                AuthIdentity.user_id == user_id, AuthIdentity.provider == provider
            )
        )

    async def first_unclaimed_user(self, emails: list[str]) -> User | None:
        """The user of the earliest of the emails who has no identity yet"""
        if not emails:
            return None
        return await self._session.scalar(
            select(User)
            .where(
                User.email.in_(emails),
                ~exists().where(AuthIdentity.user_id == User.id),
            )
            .order_by(
                case({email: i for i, email in enumerate(emails)}, value=User.email)
            )
            .limit(1)
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
        self, scope: AttemptScope, value: str, now: datetime, window_ends_at: datetime
    ) -> int:
        """Count one more attempt for the email or address in one upsert, so a burst
        cannot slip past the limit, and return its total in the window"""
        dialect = self._session.get_bind().dialect.name
        insert = postgresql.insert if dialect == "postgresql" else sqlite.insert
        ended = SignInAttempts.window_ends_at <= now
        statement = insert(SignInAttempts).values(
            scope=scope, value=value, attempts=1, window_ends_at=window_ends_at
        )
        statement = statement.on_conflict_do_update(
            index_elements=[SignInAttempts.scope, SignInAttempts.value],
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

    async def clear_sign_in_attempts(self, scope: AttemptScope, value: str) -> None:
        """Forget the attempts counted for the email or address"""
        await self._session.execute(
            delete(SignInAttempts).where(
                SignInAttempts.scope == scope, SignInAttempts.value == value
            )
        )

    async def delete_ended_sign_in_windows(self, now: datetime) -> None:
        await self._session.execute(
            delete(SignInAttempts).where(SignInAttempts.window_ends_at <= now)
        )


__all__ = ["AuthRepository"]
