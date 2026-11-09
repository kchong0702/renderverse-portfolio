from typing import Literal

from pydantic import ConfigDict, Field

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, RichValue, Value


class CustomEntry(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    title: Value
    """Main line"""

    subtitle: Value | None = None
    """Second line"""

    dates: Date | None = None
    """When"""

    location: Value | None = None
    """Where"""


class Custom(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["custom"]
    """Block kind"""

    text: RichValue | None = None
    """A paragraph before the items"""

    items: list[CustomEntry] = Field(default_factory=list)
    """Entries in display order"""
