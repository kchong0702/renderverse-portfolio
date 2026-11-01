from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from document_schema.assets import ASSET_REF, Asset, MediaType, Sha256
from document_schema.base import SchemaModel
from document_schema.content import Content
from document_schema.presentation import Presentation
from document_schema.template import Template
from document_schema.tokens import CoverLetterTokens, ResumeTokens

_IMAGE_TYPES = {MediaType.PNG, MediaType.JPEG, MediaType.WEBP}


class DocumentKind(StrEnum):
    RESUME = "resume"
    CV = "cv"
    COVER_LETTER = "cover_letter"


class BaseDocument(SchemaModel):
    format: Literal["document/v1"] = "document/v1"
    """Schema version"""

    kind: DocumentKind
    """What the document is"""

    content: Content
    """The words, independent of how they are laid out"""

    template: Template
    """Markup and styles that lay the content out"""

    presentation: Presentation = Field(default_factory=Presentation)
    """Page, token and font choices applied to the template"""

    assets: dict[Sha256, Asset] = Field(default_factory=dict)
    """Binary files the document refers to, keyed by the sha256 of their bytes"""

    def _require_asset(self, sha: str, allowed: set[MediaType], what: str) -> None:
        asset = self.assets.get(sha)
        if asset is None:
            raise ValueError(f"{what} asset {sha} is not in the document's assets")
        if asset.media_type not in allowed:
            expected = " or ".join(sorted(allowed))
            raise ValueError(
                f"{what} asset {sha} is {asset.media_type}, not {expected}"
            )

    @model_validator(mode="after")
    def _references_resolve(self) -> BaseDocument:
        for font in self.presentation.fonts:
            self._require_asset(font.sha256, {MediaType.WOFF2}, f"font {font.family!r}")
        for source in (self.template.html, self.template.css):
            for sha in ASSET_REF.findall(source):
                self._require_asset(sha, _IMAGE_TYPES, "template image")
        if self.content.header.photo is not None:
            self._require_asset(self.content.header.photo, _IMAGE_TYPES, "photo")
        tokens = self.template.tokens.model_dump()
        for name in self.presentation.token_overrides:
            if name not in tokens:
                raise ValueError(f"token override {name!r} names no template token")
        section_ids = {section.id for section in self.content.sections}
        for id_ in self.presentation.hidden:
            if id_ not in section_ids:
                raise ValueError(f"hidden id {id_!r} names no section")
        return self


class ResumeDocument(BaseDocument):
    kind: Literal[DocumentKind.RESUME, DocumentKind.CV]
    """What the document is"""

    template: Template[ResumeTokens]
    """Markup and styles that lay the content out"""


class CoverLetterDocument(BaseDocument):
    kind: Literal[DocumentKind.COVER_LETTER]
    """What the document is"""

    template: Template[CoverLetterTokens]
    """Markup and styles that lay the content out"""


Document = Annotated[ResumeDocument | CoverLetterDocument, Field(discriminator="kind")]

DOCUMENT_ADAPTER = TypeAdapter(Document)
