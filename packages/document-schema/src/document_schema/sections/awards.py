from typing import Literal

from pydantic import ConfigDict

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, Value


class Award(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    title: Value
    """Such as Dean's List"""

    awarder: Value | None = None
    """Who gave it"""

    date: Date | None = None
    """When"""


class Awards(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["awards"]
    """Block kind"""

    items: list[Award]
    """Awards in display order"""
