from pydantic import BaseModel, ConfigDict

from document_schema.types import BlockId


class Block(BaseModel):
    """Anything placeable on the page"""

    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: BlockId
    """Stable key among the document's blocks"""

    hidden: bool = False
    """Kept in the document but left off the page"""
