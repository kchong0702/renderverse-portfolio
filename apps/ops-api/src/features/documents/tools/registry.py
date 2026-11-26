from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import Tool, Tools, WriteTool
from src.core.config import DocumentsSettings
from src.features.documents.schemas import ProposeChangesetRequest, ReadDocumentRequest
from src.features.documents.tools.documents import DocumentsRequest, documents
from src.features.documents.tools.propose_changeset import propose_changeset
from src.features.documents.tools.read_document import read_document


def document_tools(
    factory: async_sessionmaker[AsyncSession], limits: DocumentsSettings
) -> Tools:
    """The documents' tools"""
    return {
        "documents": Tool(DocumentsRequest, partial(documents, factory, limits)),
        "propose_changeset": WriteTool(ProposeChangesetRequest, propose_changeset),
        "read_document": Tool(ReadDocumentRequest, partial(read_document, factory)),
    }


__all__ = ["document_tools"]
