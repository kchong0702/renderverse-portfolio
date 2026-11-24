from functools import partial
from typing import TYPE_CHECKING

from src.core.agent_runner import Tools, WriteTool
from src.features.conversations.schemas import EditDocumentsRequest
from src.features.conversations.tools.edit_documents import edit_documents

if TYPE_CHECKING:
    from src.app.container import Container


def conversation_tools(container: "Container") -> Tools:
    """The conversations' tools"""
    return {
        "edit_documents": WriteTool(
            EditDocumentsRequest, partial(edit_documents, container)
        )
    }


__all__ = ["conversation_tools"]
