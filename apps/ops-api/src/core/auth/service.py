from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.models import AuthIdentity, AuthSession, User
from src.core.auth.oauth_providers import OAuthIdentity, Provider
from src.core.auth.passwords import MIN_PASSWORD_LENGTH, hash_password, verify_password
from src.core.auth.repository import AuthRepository
from src.core.config import AuthSettings
from src.core.exceptions import Forbidden, InvalidInput, TooManyRequests, Unauthorized
from src.db.base import aware, utcnow

_RENEW_AFTER = timedelta(hours=1)

_MAX_SIGN_IN_ATTEMPTS = 5
_SIGN_IN_WINDOW = timedelta(minutes=15)


def normalise_email(email: str) -> str:
    return email.strip().lower()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(self, session: AsyncSession, settings: AuthSettings):
        """Hold the session to commit on, a repository on it, and the auth settings"""
        self._session = session
        self._repository = AuthRepository(session)
        self.settings = settings

    def is_allowed(self, email: str) -> bool:
        return normalise_email(email) in self.settings.allowed_emails

    async def dev_user(self) -> User:
        """Who every request acts as while auth is disabled"""
        return await self._user_for(normalise_email(self.settings.dev_email))

    async def sign_in_with_password(self, email: str, password: str) -> User:
        email = normalise_email(email)
        await self._count_attempt(email)
        user = await self._repository.user_by_email(email)
        matches, new_hash = verify_password(
            password, user.password_hash if user else None
        )
        if user is None or not matches or not self.is_allowed(email):
            raise Unauthorized("Wrong email or password")
        if new_hash:
            user.password_hash = new_hash
        await self._repository.clear_sign_in_attempts(email)
        return user

    async def sign_in_with_identity(
        self, provider: Provider, identity: OAuthIdentity
    ) -> User:
        """The user a Google or GitHub account belongs to, linked on first sign-in"""
        linked = await self._repository.identity(provider, identity.subject)
        if linked is not None:
            user = await self._repository.user(linked.user_id)
            if user is None or not self.is_allowed(user.email):
                raise Forbidden("This account is not allowed to sign in")
            return user

        email = next((e for e in identity.emails if self.is_allowed(e)), None)
        if email is None:
            raise Forbidden("This account is not allowed to sign in")

        user = await self._user_for(email)
        await self._repository.add(
            AuthIdentity(
                user_id=user.id,
                provider=provider,
                subject=identity.subject,
                email=email,
            )
        )
        return user

    async def create_session(self, user: User, user_agent: str = "") -> str:
        """A new session; the returned token goes in the cookie and nowhere else"""
        now = utcnow()
        await self._repository.delete_expired_sessions(user.id, now)
        token = secrets.token_urlsafe(32)
        await self._repository.add(
            AuthSession(
                user_id=user.id,
                token_hash=_hash_token(token),
                user_agent=user_agent[:255],
                created_at=now,
                last_seen_at=now,
                expires_at=now + self._idle_timeout,
            )
        )
        return token

    async def resolve_session(self, token: str) -> User | None:
        """The session's user, or None when it is unknown, expired or not allowed"""
        now = utcnow()
        session = await self._repository.live_session(_hash_token(token), now)
        if session is None:
            return None
        user = await self._repository.user(session.user_id)
        if user is None or not self.is_allowed(user.email):
            return None
        if now - aware(session.last_seen_at) > _RENEW_AFTER:
            session.last_seen_at = now
            session.expires_at = now + self._idle_timeout
        return user

    async def end_session(self, token: str) -> None:
        await self._repository.delete_session(_hash_token(token))

    async def set_password(self, email: str, password: str) -> User:
        """Set or replace a password; the email must be allowed to sign in"""
        email = normalise_email(email)
        if not self.is_allowed(email):
            raise InvalidInput(f"{email} is not in auth.allowed_emails")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidInput(
                f"A password needs at least {MIN_PASSWORD_LENGTH} characters"
            )
        user = await self._user_for(email)
        user.password_hash = hash_password(password)
        await self._repository.clear_sign_in_attempts(email)
        return user

    async def _count_attempt(self, email: str) -> None:
        """Count the attempt before checking the password, and commit it straight away
        so it stands when the sign-in fails and parallel requests see it"""
        now = utcnow()
        await self._repository.delete_ended_sign_in_windows(now)
        attempts = await self._repository.count_sign_in_attempt(
            email, now, now + _SIGN_IN_WINDOW
        )
        await self._session.commit()
        if attempts > _MAX_SIGN_IN_ATTEMPTS:
            raise TooManyRequests("Too many attempts. Try again in 15 minutes.")

    @property
    def _idle_timeout(self) -> timedelta:
        return timedelta(days=self.settings.session_idle_days)

    async def _user_for(self, email: str) -> User:
        user = await self._repository.user_by_email(email)
        if user is None:
            user = User(email=email)
            await self._repository.add(user)
        return user


__all__ = ["AuthService", "normalise_email"]
