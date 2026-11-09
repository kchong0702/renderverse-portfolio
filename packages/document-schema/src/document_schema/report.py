from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from document_schema.render_warnings import AnyRenderWarning
from document_schema.types import BlockId, FileHash


class BlockSpan(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    block: BlockId
    """The block"""

    first_page: int = Field(ge=1)
    """Page it starts on"""

    last_page: int = Field(ge=1)
    """Page it ends on"""

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        """Rejects a span that ends before it starts"""
        if self.last_page < self.first_page:
            raise ValueError(f"{self.block} ends before it starts")
        return self


class Report(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    render_id: FileHash
    """Hash of the printed PDF"""

    pages: int = Field(ge=1)
    """Number of pages"""

    last_page_fill: float = Field(ge=0, le=1)
    """How much of the last page is used"""

    spans: list[BlockSpan] = Field(default_factory=list)
    """The pages each block runs across"""

    warnings: list[AnyRenderWarning] = Field(default_factory=list)
    """Problems to fix before sending"""
