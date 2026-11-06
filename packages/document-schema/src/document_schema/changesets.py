import re
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from document_schema.edits import AnyEdit, InsertBlock, UpdateText
from document_schema.types import Id
from document_schema.values import RichValue, Value


def _sourced(value: Value | RichValue) -> bool:
    """Cites a profile fact or a line of the uploaded PDF"""
    return any(re.fullmatch(r"fact:.+|p\d+\.s\d+", src) for src in value.src)


class ChangesetStatus(StrEnum):
    PENDING = "pending"
    """Waiting for the user"""

    ACCEPTED = "accepted"
    """Applied to the document"""

    REJECTED = "rejected"
    """Turned down by the user"""


class Changeset(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    id: Id
    """Stable key; accepted wording cites it as agent:<id>"""

    agent: str
    """Which agent made it, such as career-consultant"""

    edits: list[AnyEdit] = Field(min_length=1)
    """Applied together when accepted"""

    reason: str
    """Why, in a sentence the user reads"""

    status: ChangesetStatus = ChangesetStatus.PENDING
    """Whether the user has answered"""

    @model_validator(mode="after")
    def _agent_rules(self) -> Self:
        """Rejects edits an agent may not make"""
        for edit in self.edits:
            if isinstance(edit, UpdateText) and not _sourced(edit.value):
                raise ValueError(f"{edit.path}: agent text must cite a fact or the PDF")
            if isinstance(edit, InsertBlock) and edit.block.kind == "photo":
                raise ValueError("only the user adds a photo")
            if (
                isinstance(edit, InsertBlock)
                and edit.block.kind == "letter"
                and edit.block.signature
            ):
                raise ValueError("only the user adds a signature")
        return self
