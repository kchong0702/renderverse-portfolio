from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from fastapi import Response as HTTPResponse
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.app.deps import get_chat_service, get_message_limiter
from src.app.errors import api_error, rate_limited
from src.app.request import client_ip, current_session
from src.features.chat.response import Response
from src.features.chat.schemas import Request as ChatRequest
from src.features.chat.service import ChatService
from src.features.rate_limit.message_limiter import MessageLimiter
from src.features.session.models import Session
from src.shared.exceptions import ResponseInProgressError, ResponseNotFoundError

router = APIRouter()


async def start_response(
    payload: ChatRequest,
    session: Annotated[Session, Depends(current_session)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    limiter: Annotated[MessageLimiter, Depends(get_message_limiter)],
    ip: Annotated[str, Depends(client_ip)],
) -> Response:
    if session.response is not None and not session.response.done:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "RESPONSE_IN_PROGRESS",
            "Wait for the current response to finish",
        )
    exceeded = limiter.acquire(cookie=session.cookie, ip=ip)
    if exceeded is not None:
        raise rate_limited(exceeded)
    try:
        return service.start(session, payload.message)
    except ResponseInProgressError as exc:
        raise api_error(
            status.HTTP_409_CONFLICT,
            "RESPONSE_IN_PROGRESS",
            "Wait for the current response to finish",
        ) from exc


async def resume_response(
    session: Annotated[Session, Depends(current_session)],
    service: Annotated[ChatService, Depends(get_chat_service)],
    last_event_id: Annotated[str | None, Header()] = None,
) -> tuple[Response, int]:
    try:
        return service.resume(session, last_event_id)
    except ResponseNotFoundError as exc:
        raise api_error(
            status.HTTP_404_NOT_FOUND,
            "RESPONSE_NOT_FOUND",
            "There is no response to resume",
        ) from exc


@router.post("/chat", response_class=EventSourceResponse)
async def chat(
    response: Annotated[Response, Depends(start_response)],
) -> AsyncIterator[ServerSentEvent]:
    """Stream Ezbot's response as Server-Sent Events.

    The response keeps generating if the connection drops; resume it with
    `GET /chat/stream` and the last event id, or stop it with `POST /chat/stop`.
    """
    async for event in response.stream():
        yield event


@router.get("/chat/stream", response_class=EventSourceResponse)
async def resume_chat(
    resumed: Annotated[tuple[Response, int], Depends(resume_response)],
) -> AsyncIterator[ServerSentEvent]:
    """Resume the current response after the `Last-Event-ID` the client last saw"""
    response, after = resumed
    async for event in response.stream(after):
        yield event


@router.post("/chat/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_chat(
    session: Annotated[Session, Depends(current_session)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> HTTPResponse:
    """Stop the response in progress; its stream ends with `response.cancelled`"""
    service.stop(session)
    return HTTPResponse(status_code=status.HTTP_204_NO_CONTENT)
