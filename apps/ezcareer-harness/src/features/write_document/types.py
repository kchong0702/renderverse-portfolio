from typing import TypedDict

from document_schema import AnyDocument, Changeset, FileHash
from langchain_core.messages import AnyMessage
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.shared.extraction.types import Line
from src.shared.profile import ProfileFact


class EditInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    messages: list[AnyMessage] = Field(min_length=1)
    """The user's chat, ending with their message"""

    document_id: str
    """The résumé, CV or cover letter the chat is about"""

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""


class FetchedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    document: AnyDocument
    """The document as it is now"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""

    assets: dict[FileHash, Base64Bytes] = Field(default_factory=dict)
    """The bytes of every file the document uses, which printing needs"""


class FetchFailed(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    error: str
    """Why the client couldn't send the document"""


class EditOutput(TypedDict):
    reply: str
    """The agent's answer to the user's message"""

    changeset: Changeset | None
    """The checked changeset with the page-fit deletes, when the agent proposed one"""
