from __future__ import annotations

from datetime import datetime
from uuid import UUID

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    ChangesetStatus,
    DocumentKind,
)
from pydantic import TypeAdapter
from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin


class Document(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("job_id", "kind"),
        Index(
            "uq_documents_master",
            "user_id",
            "kind",
            unique=True,
            postgresql_where=text("master"),
            sqlite_where=text("master"),
        ),
    )

    kind: Mapped[DocumentKind] = mapped_column(EnumString(DocumentKind))
    """Résumé, CV or cover letter; the same as body's kind"""

    title: Mapped[str] = mapped_column(String(200))
    """Name in the documents list, such as Résumé for Northwind Labs"""

    master: Mapped[bool] = mapped_column(default=False)
    """The one of its kind that tailored copies start from"""

    body: Mapped[AnyDocument] = mapped_column(
        PydanticJson(TypeAdapter[AnyDocument](AnyDocument))
    )
    """The current draft as document-schema's AnyDocument"""

    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), default=None
    )
    """The job it was tailored to from the master of its kind; None otherwise"""


class DocumentVersion(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "document_versions"
    __table_args__ = (UniqueConstraint("document_id", "number"),)

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    """Which document it is a copy of"""

    number: Mapped[int] = mapped_column()
    """1 for the first version of the document, counting up"""

    label: Mapped[str] = mapped_column(String(200), default="")
    """Why it was kept, such as Sent to Lumen Pay"""

    body: Mapped[AnyDocument] = mapped_column(
        PydanticJson(TypeAdapter[AnyDocument](AnyDocument))
    )
    """The document as it was"""


class DocumentChangeset(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "document_changesets"
    __table_args__ = (
        Index(
            "uq_document_changesets_pending",
            "document_id",
            unique=True,
            postgresql_where=text("status = 'pending'"),
            sqlite_where=text("status = 'pending'"),
        ),
    )

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    """The document the edits are for"""

    key: Mapped[str] = mapped_column(String(64))
    """The id the agent gave the changeset, which accepted wording cites"""

    agent: Mapped[str] = mapped_column(String(100))
    """Which agent made it, such as career-consultant"""

    reason: Mapped[str] = mapped_column(Text())
    """Why, in a sentence the user reads"""

    edits: Mapped[list[AnyEdit]] = mapped_column(
        PydanticJson(TypeAdapter(list[AnyEdit]))
    )
    """The edits, applied together when accepted"""

    status: Mapped[ChangesetStatus] = mapped_column(
        EnumString(ChangesetStatus), default=ChangesetStatus.PENDING
    )
    """Pending until the user accepts or rejects it"""

    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    """When the user answered it; None while it is pending"""

    @property
    def changeset(self) -> Changeset:
        """The proposal as the agent sent it, with its status"""
        return Changeset(
            id=self.key,
            agent=self.agent,
            edits=self.edits,
            reason=self.reason,
            status=self.status,
        )


__all__ = ["Document", "DocumentChangeset", "DocumentVersion"]
