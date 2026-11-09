from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.core.auth import CurrentUserDep
from src.features.assistant.schemas import ChatMessage
from src.features.assistant.service import AssistantService
from src.features.profile import ProfileServiceDep
from src.integrations.ezcareer import Answer, Run

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_service(
    profile: ProfileServiceDep, request: Request
) -> AssistantService:
    """The assistant service on the request's profile service"""
    return AssistantService(profile, request.app.state.ezcareer)


AssistantServiceDep = Annotated[AssistantService, Depends(get_assistant_service)]


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> Run[str]:
    """Ask career-director something in one chat; it replies, asks back with a
    widget, or fails"""
    return await service.send(user.id, chat_id, message)


@router.post("/chats/{chat_id}/tasks/{task_id}/answer")
async def answer_task(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    service: AssistantServiceDep,
) -> Run[str]:
    """Answer the widget a paused turn of the chat asked; the turn runs on"""
    return await service.answer(user.id, chat_id, task_id, answer)
