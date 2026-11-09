from typing import Literal

from pydantic import ConfigDict

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, Value


class Degree(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    degree: Value
    """Such as BSc Computer Science"""

    school: Value
    """Where it was earned"""

    dates: Date | None = None
    """When"""

    location: Value | None = None
    """Where the school is"""

    grade: Value | None = None
    """Such as First Class or GPA 3.8"""


class Education(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["education"]
    """Block kind"""

    items: list[Degree]
    """Degrees in display order"""
