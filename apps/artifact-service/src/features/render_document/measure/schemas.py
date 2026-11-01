from dataclasses import dataclass

from document_schema import DataFieldPath, LowContrast, MissingGlyph, Overflow
from pydantic import BaseModel, ConfigDict


@dataclass(frozen=True)
class MixedFontField:
    field: DataFieldPath
    """Field Chromium drew with more than one font, because the font its css asks
    for lacks some of its characters"""

    font: str
    """The font the field's css asks for, by its css family name: the first
    family in font-family the page loaded or a generic keyword, which the
    browser draws every character it can in, or else the first one listed"""


class DomFindings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bound: list[DataFieldPath]
    """Fields shown on a visible element"""

    empty: list[DataFieldPath]
    """Bound fields that show no text"""

    overflow: list[Overflow]
    """Fields whose text does not fit its box or the page"""

    lines: dict[DataFieldPath, int]
    """Lines each bound field wraps to"""

    low_contrast: list[LowContrast]
    """Fields whose text is below the WCAG AA contrast against its background"""


@dataclass(frozen=True)
class PageFindings:
    dom: DomFindings
    """What dom.js found in the laid-out page"""

    pdf: bytes
    """The page printed to PDF, returned to the caller"""

    marked_pdf: bytes
    """A second print with a link at the start and end of every field, read
    for page breaks and then thrown away"""

    missing_glyphs: list[MissingGlyph]
    """Fields with characters their font could not draw"""
