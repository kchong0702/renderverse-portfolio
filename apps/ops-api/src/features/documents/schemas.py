from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    ChangesetStatus,
    DocumentKind,
)
from pydantic import BaseModel, Field

from src.features.documents.enums import ImportStatus


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    """Name in the documents list"""

    body: AnyDocument
    """The first draft"""


class DocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    """New name; None leaves it unchanged"""


class DocumentEdits(BaseModel):
    edits: list[AnyEdit] = Field(min_length=1)
    """The user's own edits, made in order"""


class DocumentSummary(BaseModel):
    id: UUID
    """The document's id"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    title: str
    """Name in the documents list"""

    master: bool
    """The one of its kind that tailored copies start from"""

    pending_changesets: int
    """Agent changesets waiting for the user to accept or reject"""

    updated_at: datetime
    """When it last changed"""


class DocumentRead(DocumentSummary):
    body: AnyDocument
    """The current draft"""

    pending_body: AnyDocument | None
    """The draft with the pending changeset's edits applied; None when none waits"""


class VersionCreate(BaseModel):
    label: str = Field(default="", max_length=200)
    """Why it is kept, such as Sent to Lumen Pay"""


class VersionRead(BaseModel):
    id: UUID
    """The version's id"""

    number: int
    """1 for the first version, counting up"""

    label: str
    """Why it was kept"""

    created_at: datetime
    """When it was kept"""


class ChangesetRead(BaseModel):
    id: UUID
    """The stored changeset's id"""

    changeset: Changeset
    """The agent's proposal"""

    created_at: datetime
    """When the agent proposed it"""


class ChangesetDecision(BaseModel):
    status: Literal[ChangesetStatus.ACCEPTED, ChangesetStatus.REJECTED]
    """Accepted applies every edit to the document; rejected drops them all"""


class ImportRead(BaseModel):
    id: UUID
    """The import's id"""

    filename: str
    """Name of the uploaded file"""

    media_type: str
    """PDF or Word"""

    size: int
    """Bytes in the file"""

    status: ImportStatus
    """How far the import has got"""

    document_id: UUID | None
    """The draft import-resume made, once it is done"""

    error: str
    """Why the import failed; empty otherwise"""

    created_at: datetime
    """When the file was uploaded"""


__all__ = [
    "ChangesetDecision",
    "ChangesetRead",
    "DocumentCreate",
    "DocumentEdits",
    "DocumentRead",
    "DocumentSummary",
    "DocumentUpdate",
    "ImportRead",
    "VersionCreate",
    "VersionRead",
]
