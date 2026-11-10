from collections.abc import AsyncIterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.clients.ezcareer import Answer, RunStream
from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.assistant.schemas import ChatMessage
from src.features.assistant.service import AssistantService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    request: Request,
) -> AssistantService:
    """The assistant service on the request's session, its profile and settings
    services, and the app's running turns"""
    return AssistantService(
        session,
        profile,
        settings,
        request.app.state.ezcareer,
        request.app.state.runs,
        get_settings().ezcareer,
    )


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


async def start_turn(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> RunStream:
    """The turn a message starts, its profile read and committed before the response
    streams"""
    return await service.send(user.id, chat_id, message)


async def answer_turn(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> RunStream:
    """The rest of the paused turn an answer resumes, read and committed before the
    response streams"""
    return await service.answer(user.id, chat_id, task_id, answer)


def resume_turn(
    chat_id: UUID,
    user: CurrentUserDep,
    service: AssistantServiceDep,
    last_event_id: Annotated[str | None, Header()] = None,
) -> tuple[RunStream, int]:
    """The chat's current turn and how many of its events the client already has"""
    return service.resume(user.id, chat_id, last_event_id)


@router.post("/chats/{chat_id}/messages", response_class=EventSourceResponse)
async def send_message(
    run: Annotated[RunStream, Depends(start_turn)],
) -> AsyncIterable[ServerSentEvent]:
    """Ask career-director something in one chat and stream the turn: it starts,
    thinks, writes and runs steps, then replies, asks back, fails or is stopped"""
    async for event in run.stream():
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/answer", response_class=EventSourceResponse
)
async def answer_task(
    run: Annotated[RunStream, Depends(answer_turn)],
) -> AsyncIterable[ServerSentEvent]:
    """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
    async for event in run.stream():
        yield event


@router.get("/chats/{chat_id}/stream", response_class=EventSourceResponse)
async def resume_chat(
    resumed: Annotated[tuple[RunStream, int], Depends(resume_turn)],
) -> AsyncIterable[ServerSentEvent]:
    """Resume the chat's turn after the Last-Event-ID the client last saw; the turn
    kept running while the connection was down"""
    run, after = resumed
    async for event in run.stream(after):
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_task(
    chat_id: UUID, task_id: str, user: CurrentUserDep, service: AssistantServiceDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await service.cancel(user.id, chat_id, task_id)
