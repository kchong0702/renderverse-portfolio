from typing import Annotated

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


@router.post("/messages")
async def send_message(
    message: ChatMessage, user: CurrentUserDep, service: AssistantServiceDep
) -> Run[str]:
    """Ask career-director something; it replies, asks back with a widget, or fails"""
    return await service.send(user.id, message)


@router.post("/tasks/{task_id}/answer")
async def answer_task(
    task_id: str, answer: Answer, user: CurrentUserDep, service: AssistantServiceDep
) -> Run[str]:
    """Answer the widget a paused turn asked; the turn runs on from there"""
    return await service.answer(user.id, task_id, answer)
