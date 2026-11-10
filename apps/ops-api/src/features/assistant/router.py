from collections.abc import AsyncIterable
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from fastapi.sse import EventSourceResponse

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.assistant.schemas import ChatMessage
from src.features.assistant.service import AssistantService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep
from src.integrations.ezcareer import Answer, RunEvent

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    request: Request,
) -> AssistantService:
    """The assistant service on the request's session and its profile and settings
    services"""
    return AssistantService(session, profile, settings, request.app.state.ezcareer)


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


@router.post("/chats/{chat_id}/messages", response_class=EventSourceResponse)
async def send_message(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> AsyncIterable[RunEvent[str]]:
    """Ask career-director something in one chat and stream the turn: it starts,
    thinks, writes and runs steps, then replies, asks back, fails or is stopped"""
    async for event in await service.send(user.id, chat_id, message):
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/answer", response_class=EventSourceResponse
)
async def answer_task(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> AsyncIterable[RunEvent[str]]:
    """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
    async for event in await service.answer(user.id, chat_id, task_id, answer):
        yield event


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_task(
    chat_id: UUID, task_id: str, user: CurrentUserDep, service: AssistantServiceDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await service.cancel(user.id, chat_id, task_id)
