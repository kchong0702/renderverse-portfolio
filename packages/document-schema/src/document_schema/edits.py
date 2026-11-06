from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from document_schema.contents.letter import AnyLetterBlock
from document_schema.contents.resume import AnyBlock
from document_schema.enums import Region
from document_schema.types import BlockId, DataFieldPath, Id
from document_schema.values import RichValue, Value


class SetText(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["set_text"]
    """Edit kind"""

    path: DataFieldPath
    """Such as blocks/exp/items/acme/bullets/b1/text"""

    value: Value | RichValue
    """The new text"""


class InsertBlock(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["insert_block"]
    """Edit kind"""

    after: BlockId | None = None
    """None puts it first"""

    block: AnyBlock | AnyLetterBlock
    """The block to add"""


class InsertItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["insert_item"]
    """Edit kind"""

    parent: DataFieldPath
    """The list it joins, such as blocks/exp/items"""

    after: Id | None = None
    """None puts it first"""

    item: dict[str, JsonValue]
    """Checked against what the parent holds when applied"""


class Move(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["move"]
    """Edit kind"""

    path: DataFieldPath
    """What moves"""

    after: Id | None = None
    """Within the same parent; None moves it first"""


class Delete(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["delete"]
    """Edit kind"""

    path: DataFieldPath
    """What goes"""


class Place(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["place"]
    """Edit kind"""

    block: BlockId
    """What moves"""

    region: Region
    """In the document's current template"""

    after: BlockId | None = None
    """None puts it first in the region"""


class SetHidden(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["set_hidden"]
    """Edit kind"""

    block: BlockId
    """Which block"""

    hidden: bool
    """True leaves it off the page"""


class SetDesign(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    op: Literal["set_design"]
    """Edit kind"""

    changes: dict[str, JsonValue]
    """Design fields to change; checked by merging into Design when applied"""


AnyEdit = Annotated[
    SetText | InsertBlock | InsertItem | Move | Delete | Place | SetHidden | SetDesign,
    Field(discriminator="op"),
]
