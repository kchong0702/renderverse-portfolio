import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from document_schema.blocks.block import Block
from document_schema.types import Id
from document_schema.validators import require_unique_ids
from document_schema.values import RichValue, Value


class Bullet(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the entry's bullets"""

    text: RichValue
    """The bullet"""


class Link(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the entry's links"""

    url: Value
    """http or https address"""

    label: Value | None = None
    """Shown instead of the address, such as GitHub"""

    @field_validator("url")
    @classmethod
    def _url_is_http(cls, url: Value) -> Value:
        """Rejects addresses that aren't http or https"""
        if not re.fullmatch(r"https?://[^\s\"'<>]+", url.text):
            raise ValueError(f"link {url.text!r} must be an http or https address")
        return url


class Tag(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among its siblings"""

    text: Value
    """The tag, such as a skill"""


class Entry(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the section's items"""

    bullets: list[Bullet] = Field(default_factory=list)
    """In display order"""

    links: list[Link] = Field(default_factory=list)
    """In display order"""

    @model_validator(mode="after")
    def _ids_unique(self) -> Self:
        """Rejects bullets or links that share an id"""
        require_unique_ids((item.id for item in self.bullets), f"{self.id} bullets")
        require_unique_ids((item.id for item in self.links), f"{self.id} links")
        return self


class Section(Block):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    heading: Value | None = None
    """As written; None uses the template's title"""

    @model_validator(mode="after")
    def _item_ids_unique(self) -> Self:
        """Rejects items that share an id"""
        if (items := getattr(self, "items", None)) is not None:
            require_unique_ids((item.id for item in items), f"{self.id} items")
        return self
