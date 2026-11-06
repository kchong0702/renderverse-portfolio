from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from document_schema.blocks.block import Block
from document_schema.blocks.contacts import Contacts
from document_schema.blocks.photo import Photo
from document_schema.blocks.profile import Profile
from document_schema.types import FileHash, Id
from document_schema.validators import require_unique_ids
from document_schema.values import RichValue, Value


class Recipient(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["recipient"]
    """Block kind"""

    name: Value | None = None
    """Such as Aisha Rahman"""

    title: Value | None = None
    """Such as Talent Lead"""

    organization: Value | None = None
    """Such as Lumen Pay"""

    address: list[Value] = Field(default_factory=list)
    """One line each"""


class Paragraph(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the letter's paragraphs"""

    text: RichValue
    """The paragraph"""


class Letter(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["letter"]
    """Block kind"""

    date: Value | None = None
    """As written"""

    subject: Value | None = None
    """Such as Application for Senior Backend Engineer"""

    greeting: Value
    """Such as Dear Ms Rahman,"""

    paragraphs: list[Paragraph]
    """The body, in order"""

    closing: Value
    """Such as Yours sincerely,"""

    signature: FileHash | None = None
    """An image in the document's assets; set only by the user"""

    @model_validator(mode="after")
    def _ids_unique(self) -> Self:
        """Rejects paragraphs that share an id"""
        require_unique_ids(
            (item.id for item in self.paragraphs), f"{self.id} paragraphs"
        )
        return self


AnyLetterBlock = Annotated[
    Profile | Photo | Contacts | Recipient | Letter, Field(discriminator="kind")
]


class LetterContent(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    blocks: list[AnyLetterBlock]
    """Every block, in reading order"""

    @model_validator(mode="after")
    def _blocks_valid(self) -> Self:
        """Rejects a letter without one profile and one letter block, or with repeats"""
        require_unique_ids((item.id for item in self.blocks), "blocks")
        kinds = [block.kind for block in self.blocks]
        if kinds.count("profile") != 1 or kinds.count("letter") != 1:
            raise ValueError("a letter has exactly one profile and one letter")
        for kind in ("photo", "contacts", "recipient"):
            if kinds.count(kind) > 1:
                raise ValueError(f"a letter has at most one {kind}")
        return self
