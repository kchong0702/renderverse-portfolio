from collections.abc import AsyncIterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.sse import EventSourceResponse, ServerSentEvent

from src.clients.ezcareer import Answer
from src.core.auth import CurrentUserDep
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
    services, the harness and the app's run store"""
    return AssistantService(
        session,
        profile,
        settings,
        request.app.state.ezcareer,
        request.app.state.run_store,
    )


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


async def start_turn(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> str:
    """The run a message starts, its profile read and committed before the response
    streams"""
    return await service.send(user.id, chat_id, message)


async def answer_turn(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> str:
    """The run of the rest of the paused turn an answer resumes, read and committed before the
    response streams"""
    return await service.answer(user.id, chat_id, task_id, answer)


async def resume_turn(
    chat_id: UUID,
    user: CurrentUserDep,
    service: AssistantServiceDep,
    last_event_id: Annotated[str | None, Header()] = None,
) -> tuple[str, int]:
    """The chat's current run and how many of its events the client already has"""
    return await service.resume(user.id, chat_id, last_event_id)


@router.post("/chats/{chat_id}/messages", response_class=EventSourceResponse)
async def send_message(
    run_id: Annotated[str, Depends(start_turn)], request: Request
) -> AsyncIterable[ServerSentEvent]:
    """Ask career-director something in one chat and stream the turn: it starts,
    thinks, writes and runs steps, then replies, asks back, fails or is stopped"""
    async for event in request.app.state.run_store.read(run_id, 0):
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/answer", response_class=EventSourceResponse
)
async def answer_task(
    run_id: Annotated[str, Depends(answer_turn)], request: Request
) -> AsyncIterable[ServerSentEvent]:
    """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
    async for event in request.app.state.run_store.read(run_id, 0):
        yield event


@router.get("/chats/{chat_id}/stream", response_class=EventSourceResponse)
async def resume_chat(
    resumed: Annotated[tuple[str, int], Depends(resume_turn)], request: Request
) -> AsyncIterable[ServerSentEvent]:
    """Resume the chat's turn after the Last-Event-ID the client last saw; the turn
    kept running while the connection was down"""
    run_id, after = resumed
    async for event in request.app.state.run_store.read(run_id, after):
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_task(
    chat_id: UUID, task_id: str, user: CurrentUserDep, service: AssistantServiceDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await service.cancel(user.id, chat_id, task_id)
