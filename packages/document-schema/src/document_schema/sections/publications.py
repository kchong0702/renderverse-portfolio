from typing import Literal

from pydantic import ConfigDict, Field

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, Value


class Publication(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    title: Value
    """Title as published"""

    authors: list[Value] = Field(default_factory=list)
    """In the order printed"""

    venue: Value | None = None
    """Journal or conference"""

    date: Date | None = None
    """When it was published"""

    doi: Value | None = None
    """Such as 10.1145/1234567"""


class Publications(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["publications"]
    """Block kind"""

    items: list[Publication]
    """Publications in display order"""
