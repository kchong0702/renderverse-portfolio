import re
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from document_schema.blocks.block import Block
from document_schema.types import Id, require_unique_ids
from document_schema.values import RichValue, Value


class Bullet(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    text: RichValue


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
        if not re.fullmatch(r"https?://[^\s\"'<>]+", url.text):
            raise ValueError(f"link {url.text!r} must be an http or https address")
        return url


class Tag(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    text: Value


class Entry(BaseModel):
    """One item in a section, such as a job or a degree"""

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
        require_unique_ids(self.bullets, f"{self.id} bullets")
        require_unique_ids(self.links, f"{self.id} links")
        return self


class Section(Block):
    """A block with a heading and entries"""

    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    heading: Value | None = None
    """As written; None uses the template's title"""

    @model_validator(mode="after")
    def _item_ids_unique(self) -> Self:
        if (items := getattr(self, "items", None)) is not None:
            require_unique_ids(items, f"{self.id} items")
        return self
