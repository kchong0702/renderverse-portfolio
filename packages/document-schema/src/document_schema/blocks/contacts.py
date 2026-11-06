from enum import StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from document_schema.blocks.block import Block
from document_schema.types import Id
from document_schema.validators import require_unique_ids
from document_schema.values import Value


class ContactKind(StrEnum):
    EMAIL = "email"
    """Email address"""

    PHONE = "phone"
    """Phone number"""

    LOCATION = "location"
    """City or address"""

    LINKEDIN = "linkedin"
    """LinkedIn profile"""

    GITHUB = "github"
    """GitHub profile"""

    WEBSITE = "website"
    """Personal site"""

    OTHER = "other"
    """Anything else"""


class Contact(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the contacts"""

    kind: ContactKind
    """What the value is; picks the icon and label"""

    value: Value
    """As written, such as kelvin@example.com"""

    label: Value | None = None
    """Shown instead of the kind's label, such as Portfolio"""


class Contacts(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["contacts"]
    """Block kind"""

    items: list[Contact]
    """In display order"""

    @model_validator(mode="after")
    def _ids_unique(self) -> Self:
        """Rejects contacts that share an id"""
        require_unique_ids((item.id for item in self.items), f"{self.id} items")
        return self
