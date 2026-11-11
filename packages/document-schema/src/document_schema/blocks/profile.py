from typing import Literal

from pydantic import ConfigDict

from document_schema.blocks.block import Block
from document_schema.values import Value


class Profile(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["profile"]
    """Block kind"""

    name: Value
    """Full name"""

    headline: Value | None = None
    """Line under the name, such as Senior Software Engineer"""
