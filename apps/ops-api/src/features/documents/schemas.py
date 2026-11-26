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

from src.features.imports import SourceLine


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


class DocumentMatch(BaseModel):
    id: UUID
    """The document's id"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    title: str
    """Name in the documents list"""

    master: bool
    """The one of its kind that tailored copies start from"""

    updated_at: datetime
    """When it last changed"""


class DocumentSummary(DocumentMatch):
    pending_changesets: int
    """Agent changesets waiting for the user to accept or reject"""


class LineRead(BaseModel):
    id: str
    """Page and line number, such as p1.s41, which the document's values cite"""

    text: str
    """The line's text"""


class DocumentRead(DocumentSummary):
    body: AnyDocument
    """The current draft"""

    lines: list[LineRead]
    """The imported file's lines its values cite; empty for a document not imported"""

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


class DocumentContent(BaseModel):
    title: str
    """The document's title, such as Backend résumé"""

    document: AnyDocument
    """The current draft; its assets' bytes are not sent, as ops-api keeps none"""

    pdf_lines: list[SourceLine]
    """The imported file's lines; empty for a document not imported"""

    job_id: UUID | None
    """The job the document is a copy for; None for one not a job's"""


class DocumentsAnswer(BaseModel):
    documents: list[DocumentMatch]
    """The user's documents, the best match first"""


class ReadDocumentRequest(BaseModel):
    execute_tool: Literal["read_document"]
    """career-consultant asks for the document it works on"""

    document_id: UUID
    """The document to read"""


class ProposeChangesetRequest(BaseModel):
    execute_tool: Literal["propose_changeset"]
    """A paused run asks to store an agent's edits for the user to review"""

    document_id: UUID
    """The document the edits are for"""

    changeset: Changeset
    """The edits the agent proposes"""


class ChangesetStored(BaseModel):
    changeset_id: UUID
    """The pending changeset now holding the edits"""


class ChangesetArtifact(BaseModel):
    document_id: UUID
    """The document the edits are for"""

    changeset_id: UUID
    """The stored changeset propose_changeset answered with"""


class ChangesetProposed(BaseModel):
    status: Literal["changeset"] = "changeset"
    """A run proposed edits, stored for the user to review"""

    document_id: UUID
    """The document the edits are for"""

    title: str
    """The document's name"""

    changeset_id: UUID
    """The stored changeset"""

    edits: int
    """How many edits it holds"""


class TailoredDocument(BaseModel):
    document_id: UUID
    """The job's copy of the master, made the first time it is tailored"""

    tailoring: bool
    """Whether a chat turn now tailors it; False while a changeset waits for review"""


__all__ = [
    "ChangesetArtifact",
    "ChangesetDecision",
    "ChangesetProposed",
    "ChangesetRead",
    "ChangesetStored",
    "DocumentContent",
    "DocumentCreate",
    "DocumentEdits",
    "DocumentMatch",
    "DocumentRead",
    "DocumentSummary",
    "DocumentUpdate",
    "DocumentsAnswer",
    "LineRead",
    "ProposeChangesetRequest",
    "ReadDocumentRequest",
    "TailoredDocument",
    "VersionCreate",
    "VersionRead",
]
