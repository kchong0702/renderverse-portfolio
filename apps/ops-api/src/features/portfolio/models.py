from __future__ import annotations

from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import DateTime, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.portfolio.enums import MediaType
from src.features.portfolio.schemas import Snapshot


class PortfolioRelease(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "portfolio_releases"
    __table_args__ = (
        UniqueConstraint("user_id", "number"),
        Index(
            "uq_portfolio_releases_live",
            "user_id",
            unique=True,
            postgresql_where=text("live"),
            sqlite_where=text("live"),
        ),
    )

    number: Mapped[int]
    """Counts up from 1 for each user"""

    snapshot: Mapped[Snapshot] = mapped_column(PydanticJson(TypeAdapter(Snapshot)))
    """What the site shows; never changed once published"""

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
