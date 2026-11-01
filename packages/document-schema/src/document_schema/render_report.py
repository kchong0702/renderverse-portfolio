from __future__ import annotations

from pydantic import Field

from document_schema.assets import Sha256
from document_schema.base import SchemaModel
from document_schema.value import DataFieldPath


class Overflow(SchemaModel):
    field: DataFieldPath
    """Field whose text does not fit its box"""

    needed_px: float
    """Size the text needs"""

    available_px: float
    """Size the box offers"""


class LowContrast(SchemaModel):
    field: DataFieldPath
    """Field with text that is hard to read"""

    ratio: float
    """Measured contrast ratio, below the WCAG AA 4.5:1"""


class MissingGlyph(SchemaModel):
    field: DataFieldPath
    """Field containing characters the font cannot draw"""

    font: str
    """Font family that lacks the glyphs"""

    chars: str
    """The characters without glyphs"""


class RenderReport(SchemaModel):
    render_id: Sha256
    """Sha256 identifying the render these measurements belong to"""

    pages: int = Field(ge=1)
    """Number of pages rendered"""

    last_page_fill: float = Field(ge=0, le=1)
    """Fraction of the last page's height that is used"""

    overflow: list[Overflow] = Field(default_factory=list)
    """Fields whose text overflows its box"""

    low_contrast: list[LowContrast] = Field(default_factory=list)
    """Fields below the WCAG AA contrast ratio"""

    missing_glyphs: list[MissingGlyph] = Field(default_factory=list)
    """Fields containing characters the font lacks"""

    line_counts: dict[DataFieldPath, int] = Field(default_factory=dict)
    """Lines each bound field wraps to"""

    empty_fields: list[DataFieldPath] = Field(default_factory=list)
    """Bound fields that rendered no text"""

    unbound_fields: list[DataFieldPath] = Field(default_factory=list)
    """Content fields the template does not show"""

    orphan_headings: list[DataFieldPath] = Field(default_factory=list)
    """Headings left alone at the bottom of a page"""

    split_items: list[DataFieldPath] = Field(default_factory=list)
    """Items split across a page break"""
