from dependency_injector.wiring import Provide, inject
from fastapi import Depends
from langgraph.graph.state import CompiledStateGraph

from src.app.api.fastapi.v1.services.chat import ChatService
from src.app.container import Container


@inject
def get_chat_service(
    graph: CompiledStateGraph = Depends(Provide[Container.chat_graph]),  # noqa: B008
) -> ChatService:
    """Get chat service bound to the shared chat graph"""
    return ChatService(graph)
