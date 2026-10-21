from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.app.api.fastapi.deps import get_chat_service
from src.app.api.fastapi.v1.schemas.chat import Request as ChatRequest
from src.app.api.fastapi.v1.services.chat import ChatService

router = APIRouter()


@router.post("/chat", response_class=EventSourceResponse)
async def chat(
    payload: ChatRequest,
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> AsyncIterator[ServerSentEvent]:
    """Stream Ezbot's reply as Server-Sent Events.

    Clients cancel by aborting the request, which cancels the graph run.
    """
    async for event in service.stream(payload):
        yield event
