from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from document_schema.enums import Align, Font, Region
from document_schema.types import BlockId, Colour

TemplateId = Annotated[
    str, StringConstraints(pattern=r"^([a-z0-9-]{1,40}|custom-[0-9a-f-]{36})$")
]
"""A default template such as sidebar-band, or a user's custom-<uuid>"""


def _no_repeats(blocks: list[BlockId]) -> list[BlockId]:
    """Rejects a block listed twice in one region"""
    if len(blocks) != len(set(blocks)):
        raise ValueError("a block is listed twice in one region")
    return blocks


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

    layouts: dict[
        TemplateId, dict[Region, Annotated[list[BlockId], AfterValidator(_no_repeats)]]
    ] = Field(default_factory=dict)
    """Blocks the user placed, per template; the rest go where the template puts them"""

    @model_validator(mode="after")
    def _one_region_per_block(self) -> Self:
        """Rejects a block placed in two regions of one template"""
        for template, regions in self.layouts.items():
            placed = [block for blocks in regions.values() for block in blocks]
            if len(placed) != len(set(placed)):
                raise ValueError(f"a block sits in two regions of {template}")
        return self
