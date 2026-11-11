from document_schema import DocumentKind
from pydantic import BaseModel, ConfigDict


class DocumentSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    id: str
    """What edit_document takes to work on the document"""

    title: str
    """The name the user gave the document"""

    kind: DocumentKind
    """Résumé, CV or cover letter"""

    master: bool
    """Whether it is the user's master document of its kind"""

    updated_at: str
    """When the user last changed it"""


class FoundDocuments(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    documents: list[DocumentSummary]
    """The documents that match, best match first"""
