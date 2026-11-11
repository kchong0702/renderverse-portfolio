from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.sse import EventSourceResponse

from src.clients.ezcareer import Answer
from src.core.auth import CurrentUserDep
from src.features.assistant.schemas import ChatMessage
from src.features.assistant.service import AssistantService
from src.features.documents import DocumentServiceDep
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    documents: DocumentServiceDep,
    request: Request,
) -> AssistantService:
    """The assistant service on its profile, settings and documents services, the
    harness and the app's runner"""
    return AssistantService(
        profile,
        settings,
        documents,
        request.app.state.ezcareer,
        request.app.state.runner,
    )


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> EventSourceResponse:
    """Ask career-director something in one chat and stream the turn: it starts,
    thinks, writes and runs steps, then replies, asks back, fails or is stopped"""
    return EventSourceResponse(await service.send(user.id, chat_id, message))


@router.post("/chats/{chat_id}/tasks/{task_id}/answer")
async def answer_task(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> EventSourceResponse:
    """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
    return EventSourceResponse(await service.answer(user.id, chat_id, task_id, answer))


@router.get("/chats/{chat_id}/stream")
async def resume_chat(
    chat_id: UUID,
    user: CurrentUserDep,
    service: AssistantServiceDep,
    last_event_id: Annotated[str | None, Header()] = None,
) -> EventSourceResponse:
    """Resume the chat's turn after the Last-Event-ID the client last saw; the turn
    kept running while the connection was down"""
    return EventSourceResponse(await service.resume(user.id, chat_id, last_event_id))


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_task(
    chat_id: UUID, task_id: str, user: CurrentUserDep, service: AssistantServiceDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await service.cancel(user.id, chat_id, task_id)
