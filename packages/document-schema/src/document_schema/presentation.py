from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import Field, StringConstraints

from document_schema.assets import Sha256
from document_schema.base import SchemaModel
from document_schema.tokens import TokenName, TokenValue
from document_schema.value import Id

FontFamily = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9 _-]+$")]


class PageSize(StrEnum):
    A4 = "a4"
    LETTER = "letter"


class FontStyle(StrEnum):
    NORMAL = "normal"
    ITALIC = "italic"


class FontFace(SchemaModel):
    family: FontFamily
    """CSS font family name"""

    weight: int = Field(default=400, ge=100, le=900)
    """CSS font weight"""

    style: FontStyle = FontStyle.NORMAL
    """CSS font style"""

    sha256: Sha256
    """Sha256 of the woff2 asset in the document's assets"""


class Presentation(SchemaModel):
    page_size: PageSize = PageSize.A4
    """Page size the document is paginated for"""

    token_overrides: dict[TokenName, TokenValue] = Field(default_factory=dict)
    """New values for tokens the template declares, applied after its defaults"""

    fonts: list[FontFace] = Field(default_factory=list)
    """Fonts the template may use"""

    hidden: list[Id] = Field(default_factory=list)
    """Ids of sections the template does not show"""
