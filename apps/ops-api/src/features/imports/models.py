from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import TypeAdapter
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import Base, EnumString, PydanticJson, utcnow
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.imports.enums import ImportSource, ImportStatus
from src.features.imports.schemas import LookSuggestion, SourceLine


class File(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("user_id", "sha256"),)

    sha256: Mapped[str] = mapped_column(String(64))
    """Hex digest of the bytes"""

    media_type: Mapped[str] = mapped_column(String(100))
    """PDF, Word or zip"""

    size: Mapped[int] = mapped_column()
    """Bytes in the file"""

    filename: Mapped[str] = mapped_column(String(255))
    """Name the file was last uploaded under"""


class Import(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "imports"
    __table_args__ = (
        Index(
            "uq_imports_data_processing",
            "user_id",
            unique=True,
            postgresql_where=text("source = 'data' AND status = 'processing'"),
            sqlite_where=text("source = 'data' AND status = 'processing'"),
        ),
        Index(
            "uq_imports_documents_active",
            "user_id",
            unique=True,
            postgresql_where=text(
                "source = 'documents' AND status IN ('queued', 'processing')"
            ),
            sqlite_where=text(
                "source = 'documents' AND status IN ('queued', 'processing')"
            ),
        ),
    )

    file_id: Mapped[UUID] = mapped_column(ForeignKey("files.id"))
    """The uploaded file"""

    file: Mapped[File] = relationship(lazy="joined")
    """The uploaded file's row, loaded with the import"""

    source: Mapped[ImportSource] = mapped_column(EnumString(ImportSource))
    """Whether it was uploaded on the Data page or in Documents"""

    status: Mapped[ImportStatus] = mapped_column(
        EnumString(ImportStatus), default=ImportStatus.QUEUED
    )
    """How far the import has got"""

    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), default=None
    )
    """The draft a Documents import made, once it is done"""

    lines: Mapped[list[SourceLine] | None] = mapped_column(
        PydanticJson(TypeAdapter(list[SourceLine])), default=None
    )
    """The file's lines, once a Documents import is done"""

    suggestion: Mapped[LookSuggestion | None] = mapped_column(
        PydanticJson(TypeAdapter(LookSuggestion)), default=None
    )
    """The look import-resume suggests, once a Documents import is done"""

    added: Mapped[int] = mapped_column(default=0)
    """Entries, skills, links and empty fields it filled in"""

    conflicts: Mapped[int] = mapped_column(default=0)
    """Fields and matches it left for the user to settle"""

    matched: Mapped[int] = mapped_column(default=0)
    """Entries and skills it found already there"""

    claim_token: Mapped[UUID | None] = mapped_column(default=None)
    """The claim of the worker processing it"""

    lease_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the claim lapses unless the worker extends it"""

    attempts: Mapped[int] = mapped_column(default=0)
    """How many times it has been claimed"""

    run_after: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now()
    )
    """The earliest a worker may claim it"""

    error: Mapped[str] = mapped_column(Text(), default="")
    """Why the last attempt failed; empty otherwise"""

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When it was done, failed or abandoned"""


__all__ = ["File", "Import"]
