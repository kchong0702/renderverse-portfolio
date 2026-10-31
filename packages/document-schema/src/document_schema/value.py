from __future__ import annotations

from typing import Annotated

from pydantic import Field, StringConstraints

from document_schema.base import SchemaModel

Id = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+$", min_length=1)]

DataFieldPath = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z0-9_-]+(/[A-Za-z0-9_-]+)*$")
]


class Value(SchemaModel):
    text: str
    """Text as shown in the document"""

    src: list[str] = Field(default_factory=list)
    """Where the text came from: PDF span ids such as `p1.s41`,
    `fact:<id>`, or `user:<path>` for the user's own edits"""
