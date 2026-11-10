from __future__ import annotations

from base64 import b64encode
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    ChangesetStatus,
    DocumentKind,
    ResumeDocument,
)
from pydantic import BaseModel, Field, PlainSerializer

from src.features.documents.enums import ImportStatus
from src.features.documents.models import LookSuggestion, SourceLine
from src.features.profile import ProfileFact


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

    suggestion: LookSuggestion | None
    """The look the file's layout suggests, once the import is done"""

    created_at: datetime
    """When the file was uploaded"""


class DocumentMessage(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    """What the user asks edit-document about the document"""


class EditDocumentInput(BaseModel):
    document_id: UUID
    """The document to edit, which edit-document fetches from ops-api"""

    facts: list[ProfileFact]
    """The user's profile facts the edits may cite"""


class EditDocumentOutput(BaseModel):
    reply: str
    """What career-consultant tells the user"""

    changeset: Changeset | None
    """The checked edits it proposes; None when it only answered"""


class DocumentsRequest(BaseModel):
    fetch: Literal["documents"]
    """A paused run asks for the user's documents"""

    name: str | None = None
    """Words of the title the user used, such as nortwind; None lists them all"""

    kind: DocumentKind | None = None
    """Only documents of this kind; every kind when None"""


class DocumentRequest(BaseModel):
    fetch: Literal["document"]
    """A paused run asks for one of the user's documents"""

    id: UUID
    """The document"""


class DocumentsAnswer(BaseModel):
    documents: list[DocumentMatch]
    """The user's documents, the best match first"""


class DocumentAnswer(BaseModel):
    document: AnyDocument
    """The current draft; its assets' bytes are not sent, as ops-api keeps none"""

    lines: list[SourceLine]
    """The imported file's lines; empty for a document not imported"""


class FetchError(BaseModel):
    error: str
    """Why ops-api cannot answer, such as No such document"""


class ChangesetArtifact(BaseModel):
    document_id: UUID
    """The document the edits are for"""

    changeset: Changeset
    """The edits career-director proposes"""


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


class ImportResumeInput(BaseModel):
    file: Annotated[
        bytes,
        PlainSerializer(
            lambda file: b64encode(file).decode(), return_type=str, when_used="json"
        ),
    ]
    """The uploaded PDF or Word file, standard base64 in JSON"""


class ImportResumeOutput(BaseModel):
    document: ResumeDocument
    """The draft import-resume made; its pdf and report are not kept"""

    lines: list[SourceLine]
    """The file's lines, which the draft's values cite"""

    suggestion: LookSuggestion
    """The look the file's layout suggests; the draft is in its template"""


__all__ = [
    "ChangesetArtifact",
    "ChangesetDecision",
    "ChangesetProposed",
    "ChangesetRead",
    "DocumentAnswer",
    "DocumentCreate",
    "DocumentEdits",
    "DocumentMatch",
    "DocumentMessage",
    "DocumentRead",
    "DocumentRequest",
    "DocumentSummary",
    "DocumentUpdate",
    "DocumentsAnswer",
    "DocumentsRequest",
    "EditDocumentInput",
    "EditDocumentOutput",
    "FetchError",
    "ImportRead",
    "ImportResumeInput",
    "ImportResumeOutput",
    "LineRead",
    "VersionCreate",
    "VersionRead",
]
