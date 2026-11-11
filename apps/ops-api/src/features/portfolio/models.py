from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, JsonType, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.portfolio.enums import MediaType


class PortfolioRelease(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "portfolio_releases"
    __table_args__ = (UniqueConstraint("user_id", "number"),)

    number: Mapped[int]
    """Counts up from 1 for each user"""

    snapshot: Mapped[dict[str, Any]] = mapped_column(JsonType)
    """What the site shows, as a Snapshot; never changed once published"""

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    """When the release was published"""

    live: Mapped[bool] = mapped_column(default=False)
    """The release the site serves; one per user once any is published"""


class Asset(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (UniqueConstraint("user_id", "sha256"),)

    sha256: Mapped[str] = mapped_column(String(64))
    """Hex SHA-256 of the file, its key in storage under the user's id"""

    media_type: Mapped[MediaType] = mapped_column(EnumString(MediaType))
    """The file's type"""

    size: Mapped[int]
    """Bytes"""

    filename: Mapped[str] = mapped_column(String(255), default="")
    """The name the file was uploaded with"""


__all__ = ["Asset", "PortfolioRelease"]
