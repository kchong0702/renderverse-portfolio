from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from document_schema.blocks.contacts import Contact, ContactKind
from document_schema.contents.letter import AnyLetterBlock, Paragraph
from document_schema.contents.resume import AnyBlock
from document_schema.design import Design
from document_schema.sections import (
    Award,
    Bullet,
    Certification,
    CustomEntry,
    Degree,
    Job,
    LanguageSkill,
    Link,
    Project,
    Publication,
    Skill,
    Tag,
)
from document_schema.types import BlockId, DataFieldPath, Id
from document_schema.values import Date, RichValue, Value

FieldValue = Value | RichValue | Date | ContactKind | list[Value] | None
"""Any value a content field holds; None clears an optional one"""


class UpdateField(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["update_field"]
    """Edit kind"""

    path: DataFieldPath
    """Such as blocks/exp/items/acme/dates or blocks/contacts/items/c1/kind"""

    value: FieldValue
    """The field's new value; None clears an optional field"""


class InsertBlock(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["insert_block"]
    """Edit kind"""

    after: BlockId | None = None
    """None puts it first"""

    block: AnyBlock | AnyLetterBlock
    """The block to add"""


class InsertItem(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["insert_item"]
    """Edit kind"""

    parent: DataFieldPath
    """The list it joins, such as blocks/exp/items"""

    after: Id | None = None
    """None puts it first"""

    item: (
        Contact
        | Job
        | Degree
        | Project
        | Skill
        | LanguageSkill
        | Certification
        | Award
        | Publication
        | CustomEntry
        | Bullet
        | Link
        | Tag
        | Paragraph
    )
    """Shaped like the parent's items; checked against them when applied"""


class Move(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["move"]
    """Edit kind"""

    path: DataFieldPath
    """What moves"""

    after: Id | None = None
    """Within the same parent; None moves it first"""


class Delete(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["delete"]
    """Edit kind"""

    path: DataFieldPath
    """What goes"""


class UpdateVisibility(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["update_visibility"]
    """Edit kind"""

    block: BlockId
    """Which block"""

    hidden: bool
    """True leaves it off the page"""


class UpdateDesign(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["update_design"]
    """Edit kind"""

    design: Design
    """The design after the change"""


AnyEdit = Annotated[
    UpdateField
    | InsertBlock
    | InsertItem
    | Move
    | Delete
    | UpdateVisibility
    | UpdateDesign,
    Field(discriminator="kind"),
]
