from html import unescape
from typing import Annotated, Literal

import nh3
from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from document_schema.enums import Align
from document_schema.types import Source


def _keep_size(tag: str, attribute: str, value: str) -> str | None:
    """Keeps data-size only when it names a size the renderer draws"""
    if attribute == "data-size":
        return value if value in {"small", "large"} else None
    return value


def _formatting_only(html: str) -> str:
    """Removes everything but bold, italic, underline, links and text size"""
    return nh3.clean(
        html,
        tags={"b", "i", "u", "a", "span"},
        attributes={"a": {"href"}, "span": {"data-size"}},
        attribute_filter=_keep_size,
        url_schemes={"http", "https"},
        link_rel=None,
    )


class Value(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    text: str
    """Text as shown"""

    src: list[Source] = Field(default_factory=list)
    """Where the text came from"""


class RichValue(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    html: Annotated[str, AfterValidator(_formatting_only)]
    """Text with its formatting; other markup is removed"""

    align: Align | None = None
    """Paragraph alignment; None follows the document"""

    src: list[Source] = Field(default_factory=list)
    """Where the text came from"""

    @property
    def text(self) -> str:
        """The text without formatting"""
        return unescape(nh3.clean(self.html, tags=set()))


class Date(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    text: Value
    """As written, such as 2022 to now"""

    start: Annotated[str, StringConstraints(pattern=r"^\d{4}(-\d{2})?$")] | None = None
    """YYYY or YYYY-MM"""

    end: (
        Annotated[str, StringConstraints(pattern=r"^\d{4}(-\d{2})?$")]
        | Literal["present"]
        | None
    ) = None
    """YYYY, YYYY-MM or present; None for a single date"""
