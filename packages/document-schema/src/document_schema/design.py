from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from document_schema.enums import Align, Font, Region
from document_schema.types import BlockId, Colour

TemplateId = Annotated[
    str, StringConstraints(pattern=r"^([a-z0-9-]{1,40}|custom-[0-9a-f-]{36})$")
]
"""A default template such as sidebar-band, or a user's custom-<uuid>"""


class PageSize(StrEnum):
    A4 = "a4"
    """210 by 297 mm"""

    LETTER = "letter"
    """8.5 by 11 inches"""


class Size(StrEnum):
    SMALL = "small"
    """Smaller than usual"""

    MEDIUM = "medium"
    """The usual size"""

    LARGE = "large"
    """Larger than usual"""


class PhotoShape(StrEnum):
    CIRCLE = "circle"
    """Round"""

    ROUNDED = "rounded"
    """Square with rounded corners"""

    SQUARE = "square"
    """Square corners"""


class Placement(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    template: TemplateId
    """The template this placement applies to"""

    region: Region
    """Where in that template the blocks go"""

    blocks: list[BlockId]
    """The blocks the user put there, in order"""


class Design(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    template: TemplateId = "classic"
    """The template the document is laid out with"""

    accent: Colour | None = None
    """None uses the template's colour"""

    font: Font | None = None
    """A bundled font; None uses the template's"""

    text_size: Size = Size.MEDIUM
    """Size of body text"""

    line_spacing: float = Field(1.3, ge=1.05, le=1.7)
    """Line height as a multiple of the text size"""

    alignment: Literal[Align.LEFT, Align.JUSTIFY] = Align.LEFT
    """How body text lines up"""

    margins_mm: float = Field(16, ge=8, le=25)
    """Page margins"""

    section_spacing_pt: float = Field(12, ge=4, le=24)
    """Space between blocks"""

    page_size: PageSize = PageSize.A4
    """Paper size"""

    photo_shape: PhotoShape = PhotoShape.CIRCLE
    """Shape of the photo"""

    photo_size: Size = Size.MEDIUM
    """Size of the photo"""

    layouts: list[Placement] = Field(default_factory=list)
    """Blocks the user placed, per template; the rest go where the template puts them"""

    @model_validator(mode="after")
    def _placed_once(self) -> Self:
        """Rejects a region listed twice, or a block placed twice, in one template"""
        regions = [(placement.template, placement.region) for placement in self.layouts]
        if len(regions) != len(set(regions)):
            raise ValueError("a template lists one region twice")
        blocks = [
            (placement.template, block)
            for placement in self.layouts
            for block in placement.blocks
        ]
        if len(blocks) != len(set(blocks)):
            raise ValueError("a block is placed twice in one template")
        return self
