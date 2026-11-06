from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, model_validator

from document_schema.sections.section import Section, Tag
from document_schema.types import Id, require_unique_ids
from document_schema.values import Value


class Skill(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the section's skills"""

    label: Value | None = None
    """Such as Languages; None shows just the items"""

    items: list[Tag]
    """Such as Python, TypeScript"""

    @model_validator(mode="after")
    def _ids_unique(self) -> Self:
        require_unique_ids(self.items, f"{self.id} items")
        return self


class Skills(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["skills"]
    """Block kind"""

    items: list[Skill]
    """Skill rows in display order"""
