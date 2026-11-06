from typing import Literal, Self

from pydantic import ConfigDict, Field, model_validator

from document_schema.sections.section import Entry, Section, Tag
from document_schema.types import require_unique_ids
from document_schema.values import Date, RichValue, Value


class Project(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    name: Value
    """Project name"""

    role: Value | None = None
    """What the user did on it"""

    dates: Date | None = None
    """When"""

    description: RichValue | None = None
    """What it is"""

    tags: list[Tag] = Field(default_factory=list)
    """Tech stack, in display order"""

    @model_validator(mode="after")
    def _tag_ids_unique(self) -> Self:
        require_unique_ids(self.tags, f"{self.id} tags")
        return self


class Projects(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["projects"]
    """Block kind"""

    items: list[Project]
    """Projects in display order"""
