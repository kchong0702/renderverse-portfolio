from typing import Literal

from pydantic import ConfigDict

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, RichValue, Value


class Job(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    role: Value
    """Job title"""

    company: Value
    """Employer"""

    dates: Date | None = None
    """When, such as 2022 to now"""

    location: Value | None = None
    """Where"""

    description: RichValue | None = None
    """A paragraph before the bullets"""


class Experience(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["experience"]
    """Block kind"""

    items: list[Job]
    """Jobs in display order"""
