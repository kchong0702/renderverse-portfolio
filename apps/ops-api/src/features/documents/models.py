from __future__ import annotations

from uuid import UUID

from document_schema import AnyDocument, Changeset, DocumentKind
from pydantic import TypeAdapter
from sqlalchemy import (
    ForeignKey,
    Index,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import Base, EnumString, PydanticJson
from src.db.mixins import AuditMixin, IdMixin, UserScopedMixin
from src.features.documents.enums import ImportStatus
from src.features.documents.schemas import LookSuggestion, SourceLine


class Document(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "documents"
    __table_args__ = (
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

    lines: Mapped[list[SourceLine]] = mapped_column(
        PydanticJson(TypeAdapter(list[SourceLine])), default=list
    )
    """The imported file's lines, which edit-document checks citations against;
    empty for a document not imported"""


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

    document_id: Mapped[UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )
    """The document the edits are for"""

    changeset: Mapped[Changeset] = mapped_column(PydanticJson(TypeAdapter(Changeset)))
    """An agent's proposal; its status turns accepted or rejected when the user
    answers it"""


class DocumentImport(IdMixin, UserScopedMixin, AuditMixin, Base):
    __tablename__ = "document_imports"

    filename: Mapped[str] = mapped_column(String(255))
    """Name of the uploaded file"""

    media_type: Mapped[str] = mapped_column(String(100))
    """PDF or Word"""

    size: Mapped[int] = mapped_column()
    """Bytes in the file"""

    content: Mapped[bytes] = mapped_column(LargeBinary(), deferred=True)
    """The file itself; loaded only when asked for"""

    status: Mapped[ImportStatus] = mapped_column(
        EnumString(ImportStatus), default=ImportStatus.PENDING
    )
    """How far the import has got"""

    document_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), default=None
    )
    """The draft import-resume made, once it is done"""

    error: Mapped[str] = mapped_column(Text(), default="")
    """Why the import failed; empty otherwise"""

    suggestion: Mapped[LookSuggestion | None] = mapped_column(
        PydanticJson(TypeAdapter(LookSuggestion)), default=None
    )
    """The look import-resume suggests from the file's layout, once it is done"""


__all__ = [
    "Document",
    "DocumentChangeset",
    "DocumentImport",
    "DocumentVersion",
    "LookSuggestion",
    "SourceLine",
]
