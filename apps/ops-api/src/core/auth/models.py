from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.auth.enums import AttemptScope, IdentityProvider, Role
from src.db.base import Base, EnumString, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin


class User(IdMixin, AuditMixin, Base):
    """Whoever a request acts for; every feature table points here through user_id"""

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("email = lower(trim(email))", name="email_normalised"),
        CheckConstraint("role in ('admin', 'user')", name="role"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True)
    """Lowercased and trimmed; only seeded users can sign in"""

    role: Mapped[Role] = mapped_column(
        EnumString(Role), default=Role.USER, server_default=Role.USER.value
    )
    """Only an admin can use the portfolio; set in the database"""

    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """When access was revoked; None while the user can sign in"""


class AuthIdentity(IdMixin, UserScopedMixin, Base):
    """One way a user signs in: a password, a Google account or a GitHub account"""

    __tablename__ = "auth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject"),
        UniqueConstraint("user_id", "provider"),
        CheckConstraint(
            "provider in ('password', 'google', 'github')", name="provider"
        ),
        CheckConstraint("(provider = 'password') = (subject is null)", name="subject"),
        CheckConstraint(
            "(provider = 'password') = (secret_hash is not null)", name="secret_hash"
        ),
    )

    provider: Mapped[IdentityProvider] = mapped_column(EnumString(IdentityProvider))
    """How the user signs in"""

    subject: Mapped[str | None] = mapped_column(String(255))
    """The provider's stable account id; None for a password"""

    email: Mapped[str] = mapped_column(String(320))
    """The verified email when it was linked"""

    secret_hash: Mapped[str | None] = mapped_column(String(255))
    """The password's Argon2id hash; None for Google and GitHub"""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class AuthSession(IdMixin, UserScopedMixin, Base):
    """A signed-in browser; the cookie holds the token, only its hash is stored"""

    __tablename__ = "auth_sessions"

    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SignInAttempts(Base):
    """Password sign-ins for one typed email or one client address in its current
    window; unknown emails are limited the same way, so a 429 reveals no accounts"""

    __tablename__ = "auth_sign_in_attempts"

    scope: Mapped[AttemptScope] = mapped_column(
        EnumString(AttemptScope), primary_key=True
    )
    """Whether value is an email or a client address"""

    value: Mapped[str] = mapped_column(String(320), primary_key=True)
    """The typed email, normalised, or the client address"""

    attempts: Mapped[int] = mapped_column(Integer)
    window_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


__all__ = ["AuthIdentity", "AuthSession", "SignInAttempts", "User"]
