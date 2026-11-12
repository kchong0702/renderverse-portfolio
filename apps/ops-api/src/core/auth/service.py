from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth.enums import AttemptScope, IdentityProvider, Role
from src.core.auth.models import AuthIdentity, AuthSession, User
from src.core.auth.oauth_providers import OAuthIdentity, Provider
from src.core.auth.passwords import MIN_PASSWORD_LENGTH, hash_password, verify_password
from src.core.auth.repository import AuthRepository
from src.core.config import AuthSettings
from src.core.exceptions import (
    Conflict,
    Forbidden,
    InvalidInput,
    NotFound,
    TooManyRequests,
    Unauthorized,
)
from src.db.base import as_utc, utcnow

_RENEW_AFTER = timedelta(hours=1)

_MAX_SIGN_IN_ATTEMPTS = {AttemptScope.EMAIL: 5, AttemptScope.IP: 20}
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

    async def dev_user(self) -> User:
        """Who every request acts as while auth is disabled, always an admin"""
        email = normalise_email(self.settings.dev_email)
        user = await self._repository.user_by_email(email)
        if user is None:
            user = await self._repository.add(User(email=email))
        user.role = Role.ADMIN
        return user

    async def sign_in_with_password(
        self, email: str, password: str, address: str
    ) -> User:
        """The seeded, enabled user whose password this is, counted against the
        email's and the client address's limits"""
        email = normalise_email(email)
        await self._count_attempt(email, address)
        user = await self._repository.user_by_email(email)
        identity = (
            await self._repository.user_identity(user.id, IdentityProvider.PASSWORD)
            if user
            else None
        )
        matches, new_hash = verify_password(
            password, identity.secret_hash if identity else None
        )
        if (
            user is None
            or identity is None
            or not matches
            or user.disabled_at is not None
        ):
            raise Unauthorized("Wrong email or password")
        if new_hash:
            identity.secret_hash = new_hash
        await self._repository.clear_sign_in_attempts(AttemptScope.EMAIL, email)
        return user

    async def sign_in_with_identity(
        self, provider: Provider, identity: OAuthIdentity
    ) -> User:
        """The user a Google or GitHub account is linked to, or the first of its emails'
        seeded users with no sign-in method yet, who it is then linked to"""
        linked = await self._repository.identity(provider, identity.subject)
        user = (
            await self._repository.user(linked.user_id)
            if linked
            else await self._repository.first_unclaimed_user(identity.emails)
        )
        if user is None or user.disabled_at is not None:
            raise Forbidden("This account is not allowed to sign in")
        if linked is None:
            await self._repository.add(
                AuthIdentity(
                    user_id=user.id,
                    provider=provider,
                    subject=identity.subject,
                    email=user.email,
                )
            )
        return user

    async def identities(self, user: User) -> list[AuthIdentity]:
        """Every way the user signs in"""
        return await self._repository.identities(user.id)

    async def link_identity(
        self, user: User, provider: Provider, identity: OAuthIdentity
    ) -> None:
        """Add a Google or GitHub account as one more way the user signs in"""
        linked = await self._repository.identity(provider, identity.subject)
        if linked is not None and linked.user_id == user.id:
            return
        if linked is not None:
            raise Conflict(f"This {provider} account is linked to someone else")
        if await self._repository.user_identity(user.id, IdentityProvider(provider)):
            raise Conflict(f"You already have a {provider} account linked")
        if not identity.emails:
            raise InvalidInput(f"This {provider} account has no verified email")
        await self._repository.add(
            AuthIdentity(
                user_id=user.id,
                provider=provider,
                subject=identity.subject,
                email=identity.emails[0],
            )
        )

    async def unlink(self, user: User, provider: IdentityProvider) -> None:
        """Remove one way the user signs in, never the last one"""
        identities = await self._repository.identities(user.id)
        identity = next((i for i in identities if i.provider == provider), None)
        if identity is None:
            raise NotFound(f"No {provider} sign-in is linked")
        if len(identities) == 1:
            raise Conflict("You can't remove your last sign-in method")
        await self._repository.delete(identity)

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
        """The session's user, or None when it is unknown, expired or disabled"""
        now = utcnow()
        session = await self._repository.live_session(_hash_token(token), now)
        if session is None:
            return None
        user = await self._repository.user(session.user_id)
        if user is None or user.disabled_at is not None:
            return None
        if now - as_utc(session.last_seen_at) > _RENEW_AFTER:
            session.last_seen_at = now
            session.expires_at = now + self._idle_timeout
        return user

    async def end_session(self, token: str) -> None:
        await self._repository.delete_session(_hash_token(token))

    async def set_password(self, email: str, password: str) -> User:
        """Set or replace the password of a seeded, enabled user"""
        email = normalise_email(email)
        user = await self._repository.user_by_email(email)
        if user is None:
            raise InvalidInput(f"{email} is not a user")
        if user.disabled_at is not None:
            raise InvalidInput(f"{email} is disabled")
        if len(password) < MIN_PASSWORD_LENGTH:
            raise InvalidInput(
                f"A password needs at least {MIN_PASSWORD_LENGTH} characters"
            )
        identity = await self._repository.user_identity(
            user.id, IdentityProvider.PASSWORD
        )
        if identity is None:
            await self._repository.add(
                AuthIdentity(
                    user_id=user.id,
                    provider=IdentityProvider.PASSWORD,
                    email=email,
                    secret_hash=hash_password(password),
                )
            )
        else:
            identity.secret_hash = hash_password(password)
        await self._repository.clear_sign_in_attempts(AttemptScope.EMAIL, email)
        return user

    async def _count_attempt(self, email: str, address: str) -> None:
        """Count the attempt for the email and the address before checking the password,
        and commit it straight away so it stands when the sign-in fails"""
        now = utcnow()
        await self._repository.delete_ended_sign_in_windows(now)
        over = False
        for scope, value in ((AttemptScope.EMAIL, email), (AttemptScope.IP, address)):
            attempts = await self._repository.count_sign_in_attempt(
                scope, value, now, now + _SIGN_IN_WINDOW
            )
            over = over or attempts > _MAX_SIGN_IN_ATTEMPTS[scope]
        await self._session.commit()
        if over:
            raise TooManyRequests("Too many attempts. Try again in 15 minutes.")

    @property
    def _idle_timeout(self) -> timedelta:
        return timedelta(days=self.settings.session_idle_days)


__all__ = ["AuthService", "normalise_email"]
