from __future__ import annotations

from uuid import UUID

from sqlalchemy import ForeignKey, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base
from src.db.mixins import AuditMixin


class GoogleAccount(AuditMixin, Base):
    __tablename__ = "google_accounts"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    """Whose Google account it is; each user connects at most one"""

    email: Mapped[str] = mapped_column(String(320))
    """The Gmail address Ops reads"""

    ciphertext: Mapped[bytes] = mapped_column(LargeBinary)
    """The offline refresh token, encrypted with Fernet under google.encryption_key"""

    scopes: Mapped[str] = mapped_column(Text(), server_default="")
    """Space-separated scopes the grant allows; empty for older grants"""


__all__ = ["GoogleAccount"]
