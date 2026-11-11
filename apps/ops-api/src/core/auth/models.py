from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.core.auth.enums import Role
from src.db.base import Base, EnumString, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin


class User(IdMixin, AuditMixin, Base):
    """Whoever a request acts for; every feature table points here through user_id"""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True)
    """Lowercased; must be in auth.allowed_emails to sign in"""

    password_hash: Mapped[str | None] = mapped_column(String(255))
    """Argon2 hash; None until a password is set with the CLI"""

    role: Mapped[Role] = mapped_column(
        EnumString(Role), default=Role.USER, server_default=Role.USER.value
    )
    """Only an admin can use the portfolio; set in the database"""


class AuthIdentity(IdMixin, UserScopedMixin, Base):
    """A Google or GitHub account linked to a user through a verified email"""

    __tablename__ = "auth_identities"
    __table_args__ = (UniqueConstraint("provider", "subject"),)

    provider: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(255))
    """The provider's stable account id"""

    email: Mapped[str] = mapped_column(String(320))
    """The verified email it signed in with"""

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
    """Password sign-ins for one email in its current window.

    Keyed by the email typed, not a user, so unknown emails are limited the same way
    and a 429 never tells which emails have accounts."""

    __tablename__ = "auth_sign_in_attempts"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    attempts: Mapped[int] = mapped_column(Integer)
    window_ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


__all__ = ["AuthIdentity", "AuthSession", "SignInAttempts", "User"]
