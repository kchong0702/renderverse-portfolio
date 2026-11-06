from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from document_schema.enums import Region
from document_schema.types import BlockId, DataFieldPath


class RenderWarning(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )


class SplitEntry(RenderWarning):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["split_entry"]
    """Warning kind"""

    path: DataFieldPath
    """The entry"""

    pages: tuple[int, int]
    """The page it starts on and the page it ends on"""


class OrphanHeading(RenderWarning):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["orphan_heading"]
    """Warning kind"""

    block: BlockId
    """The section"""

    page: int
    """Where the heading sits alone at the bottom"""


class RegionOverflow(RenderWarning):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["region_overflow"]
    """Warning kind"""

    region: Region
    """The region"""

    by_mm: float
    """How far past the page it runs"""


AnyRenderWarning = Annotated[
    SplitEntry | OrphanHeading | RegionOverflow, Field(discriminator="kind")
]
