from typing import Literal

from pydantic import ConfigDict

from document_schema.sections.section import Entry, Section
from document_schema.values import Date, Value


class Certification(Entry):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    name: Value
    """Such as AWS Solutions Architect"""

    issuer: Value | None = None
    """Who awarded it"""

    date: Date | None = None
    """When it was earned"""


class Certifications(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["certifications"]
    """Block kind"""

    items: list[Certification]
    """Certifications in display order"""
