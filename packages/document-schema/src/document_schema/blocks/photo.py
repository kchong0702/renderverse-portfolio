from typing import Literal

from pydantic import ConfigDict

from document_schema.blocks.block import Block
from document_schema.types import FileHash


class Photo(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["photo"]
    """Block kind"""

    file: FileHash
    """The image in the document's assets; set only by the user"""
