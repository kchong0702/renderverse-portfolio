from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, StringConstraints


def clipped(limit: int) -> AfterValidator:
    """A validator that cuts text to its first limit characters"""
    return AfterValidator(lambda text: text[:limit])


YearMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")]
"""A month as YYYY-MM"""

LooseMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}(-(0[1-9]|1[0-2]))?$")]
"""A month as YYYY-MM, or only its year as YYYY when an import gives no month"""

EntryEnd = YearMonth | Literal["present"]
"""The last month of an entry, or present while it is ongoing"""

FactId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""Key the agents cite as fact:<id>"""

Highlight = Annotated[str, StringConstraints(min_length=1)]
"""One achievement sentence"""

Link = Annotated[str, StringConstraints(min_length=1, max_length=500)]
"""A URL"""

Tool = Annotated[str, StringConstraints(min_length=1, max_length=50)]
"""A language, framework or tool a project used, such as React or Figma"""

ChangeField = Literal[
    "name",
    "headline",
    "location",
    "email",
    "phone",
    "summary",
    "title",
    "organisation",
    "start",
    "end",
    "highlights",
    "link",
    "code_link",
    "tools",
]
"""A profile or entry field an import can change"""

FieldValue = str | list[str] | None
"""A field's value: text, a list such as highlights, or None for a missing link"""


__all__ = [
    "ChangeField",
    "EntryEnd",
    "FactId",
    "FieldValue",
    "Highlight",
    "Link",
    "LooseMonth",
    "Tool",
    "YearMonth",
    "clipped",
]
