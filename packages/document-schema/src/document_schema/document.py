from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from document_schema.contents.letter import AnyLetterBlock, LetterContent
from document_schema.contents.resume import AnyBlock, ResumeContent
from document_schema.design import Design
from document_schema.types import FileHash


def _check_references(
    blocks: Sequence[AnyBlock | AnyLetterBlock],
    design: Design,
    assets: dict[FileHash, Asset],
) -> None:
    """Every file and block the document points at exists"""
    files = [block.file for block in blocks if block.kind == "photo"]
    files += [
        block.signature
        for block in blocks
        if block.kind == "letter" and block.signature
    ]
    if missing := [file for file in files if file not in assets]:
        raise ValueError(f"files not in assets: {missing}")
    ids = {block.id for block in blocks}
    for template, regions in design.layouts.items():
        placed = {block for blocks in regions.values() for block in blocks}
        if unknown := placed - ids:
            raise ValueError(
                f"layout for {template} places unknown blocks: {sorted(unknown)}"
            )


class DocumentKind(StrEnum):
    RESUME = "resume"
    CV = "cv"
    COVER_LETTER = "cover_letter"


class MediaType(StrEnum):
    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"


class Asset(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    media_type: MediaType
    """Kind of image"""

    uri: str
    """Where ops keeps the file"""


class Document(BaseModel):
    """What every document has"""

    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    format: Literal["document/v2"] = "document/v2"
    """Schema version"""

    language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$")] = (
        "en"
    )
    """For default headings, such as en or ms-MY"""

    design: Design = Field(default_factory=Design)
    """How it looks"""

    assets: dict[FileHash, Asset] = Field(default_factory=dict)
    """Files it uses, by hash"""


class ResumeDocument(Document):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal[DocumentKind.RESUME, DocumentKind.CV]
    """Résumé or CV"""

    content: ResumeContent
    """The words"""

    @model_validator(mode="after")
    def _references_exist(self) -> Self:
        _check_references(self.content.blocks, self.design, self.assets)
        return self


class LetterDocument(Document):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal[DocumentKind.COVER_LETTER]
    """Cover letter"""

    content: LetterContent
    """The words"""

    matches: UUID | None = None
    """The résumé whose design this letter follows"""

    @model_validator(mode="after")
    def _references_exist(self) -> Self:
        _check_references(self.content.blocks, self.design, self.assets)
        return self


AnyDocument = Annotated[ResumeDocument | LetterDocument, Field(discriminator="kind")]
