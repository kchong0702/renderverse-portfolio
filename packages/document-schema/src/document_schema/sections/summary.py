from typing import Literal

from pydantic import ConfigDict

from document_schema.sections.section import Section
from document_schema.values import RichValue


class Summary(Section):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    kind: Literal["summary"]
    """Block kind"""

    text: RichValue
    """The paragraph"""
