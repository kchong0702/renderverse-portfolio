from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.providers import Provider
from src.db.base import Base, EnumString, PydanticJson, utcnow
from src.db.mixins import AuditMixin
from src.features.connections.schemas import ConnectionDetails


class Connection(AuditMixin, Base):
    __tablename__ = "connections"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    """Whose connection it is"""

    provider: Mapped[Provider] = mapped_column(EnumString(Provider), primary_key=True)
    """The outside service; each user connects it at most once"""

    account: Mapped[str] = mapped_column(String(320), default="")
    """The connected account, such as the Gmail address; empty when there is none"""

    secret: Mapped[bytes] = mapped_column(LargeBinary)
    """The token or API key, encrypted with Fernet under the provider's encryption_key"""

    details: Mapped[ConnectionDetails] = mapped_column(
        PydanticJson(TypeAdapter[ConnectionDetails](ConnectionDetails))
    )
    """What the provider keeps beyond the shared columns, such as scopes or quota"""

    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    """When the current secret was stored"""


__all__ = ["Connection"]
