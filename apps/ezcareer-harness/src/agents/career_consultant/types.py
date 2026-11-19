from document_schema import AnyDocument, FileHash
from pydantic import Base64Bytes, BaseModel, ConfigDict, Field

from src.shared.extraction.types import Line


class LoadedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    document: AnyDocument
    """The document as it is now"""

    lines: list[Line]
    """The uploaded PDF's lines, which the document cites as p<page>.s<n>"""

    assets: dict[FileHash, Base64Bytes] = Field(default_factory=dict)
    """The bytes of every file the document uses, which printing needs"""
