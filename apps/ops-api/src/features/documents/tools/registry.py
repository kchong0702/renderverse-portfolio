from functools import partial

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.agent_runner import Tool, Tools
from src.core.config import DocumentsSettings
from src.features.documents.tools.document import DocumentRequest, document
from src.features.documents.tools.documents import DocumentsRequest, documents


def document_tools(
    factory: async_sessionmaker[AsyncSession], limits: DocumentsSettings
) -> Tools:
    """The documents' tools"""
    return {
        "document": Tool(DocumentRequest, partial(document, factory)),
        "documents": Tool(DocumentsRequest, partial(documents, factory, limits)),
    }


__all__ = ["document_tools"]
