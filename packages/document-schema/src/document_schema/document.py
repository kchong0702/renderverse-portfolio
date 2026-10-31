from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field, model_validator

from document_schema.assets import Asset, MediaType, Sha256
from document_schema.base import SchemaModel
from document_schema.content import Content
from document_schema.presentation import Presentation
from document_schema.template import Template

_IMAGE_TYPES = {MediaType.PNG, MediaType.JPEG, MediaType.WEBP}


class DocumentKind(StrEnum):
    RESUME = "resume"
    CV = "cv"
    COVER_LETTER = "cover_letter"


class Document(SchemaModel):
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

    @model_validator(mode="after")
    def _references_resolve(self) -> Document:
        for font in self.presentation.fonts:
            if self._media_type(font.sha256) is not MediaType.WOFF2:
                raise ValueError(
                    f"font {font.family!r} needs a font/woff2 asset"
                    f" with sha256 {font.sha256}"
                )
        photo = self.content.header.photo
        if photo is not None and self._media_type(photo) not in _IMAGE_TYPES:
            raise ValueError(f"photo needs an image asset with sha256 {photo}")
        for name in self.presentation.token_overrides:
            if name not in self.template.tokens:
                raise ValueError(f"token override {name!r} names no template token")
        section_ids = {section.id for section in self.content.sections}
        for id_ in self.presentation.hidden:
            if id_ not in section_ids:
                raise ValueError(f"hidden id {id_!r} names no section")
        return self

    def _media_type(self, sha: str) -> MediaType | None:
        asset = self.assets.get(sha)
        return asset.media_type if asset else None
