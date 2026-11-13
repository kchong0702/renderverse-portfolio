from __future__ import annotations

from base64 import b64encode
from datetime import datetime
from typing import Annotated
from uuid import UUID

from document_schema import ResumeDocument
from pydantic import BaseModel, Field, PlainSerializer

from src.features.imports.enums import ImportSource, ImportStatus, LookTrait


class SourceLine(BaseModel):
    id: str = Field(pattern=r"^p\d+\.s\d+$")
    """Page and line number, such as p1.s41, which the document's values cite"""

    text: str
    """The line's text"""

    page: int = Field(ge=1)
    """Page it is on"""

    x0: float
    """Left edge, in points from the page's left"""

    top: float
    """Top edge, in points from the page's top"""

    x1: float
    """Right edge, in points from the page's left"""

    bottom: float
    """Bottom edge, in points from the page's top"""


class LookSuggestion(BaseModel):
    template: str = Field(pattern=r"^[a-z0-9-]{1,40}$")
    """The document-renderer template closest to the file's layout"""

    columns: int = Field(ge=1, le=2)
    """How many columns the file's pages are set in"""

    traits: list[LookTrait]
    """What else the file's layout has, which the template was picked by"""


class ImportRead(BaseModel):
    id: UUID
    """The import's id"""

    source: ImportSource
    """Whether it was uploaded on the Data page or in Documents"""

    filename: str
    """Name of the uploaded file"""

    media_type: str
    """PDF, Word or zip"""

    size: int
    """Bytes in the file"""

    status: ImportStatus
    """How far the import has got"""

    document_id: UUID | None
    """The draft a Documents import made, once it is done"""

    suggestion: LookSuggestion | None
    """The look the file's layout suggests, once a Documents import is done"""

    added: int
    """Entries, skills, links and empty fields it filled in"""

    conflicts: int
    """Fields and matches it left for the user to settle"""

    matched: int
    """Entries and skills it found already there"""

    error: str
    """Why the last attempt failed; empty otherwise"""

    created_at: datetime
    """When the file was uploaded"""

    finished_at: datetime | None
    """When it was done, failed or abandoned; None while it is queued or processing"""


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
    "ImportRead",
    "ImportResumeInput",
    "ImportResumeOutput",
    "LookSuggestion",
    "SourceLine",
]
