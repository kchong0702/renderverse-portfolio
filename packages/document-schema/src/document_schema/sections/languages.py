from typing import Literal

from pydantic import BaseModel, ConfigDict

from document_schema.sections.section import Section
from document_schema.types import Id
from document_schema.values import Value


class LanguageSkill(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key among the section's languages"""

    language: Value
    """Such as Malay"""

    fluency: Value | None = None
    """Such as Native or C1"""


class Languages(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["languages"]
    """Block kind"""

    items: list[LanguageSkill]
    """Languages in display order"""
