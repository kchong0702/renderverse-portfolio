from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, status
from fastapi.sse import EventSourceResponse

from src.clients.ezcareer import Answer
from src.core.auth import CurrentUserDep
from src.features.assistant.chat import AssistantChat
from src.features.assistant.profile_edits import ProfileEdits
from src.features.assistant.schemas import ChatMessage, ProfileDecision
from src.features.documents import DocumentServiceDep
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/assistant", tags=["assistant"])


def get_assistant_chat(
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    documents: DocumentServiceDep,
    request: Request,
) -> AssistantChat:
    """The assistant chat on its profile, settings and documents services, the
    profile edits and the app's runner"""
    return AssistantChat(
        profile,
        settings,
        documents,
        ProfileEdits(request.app.state.session_factory),
        request.app.state.runner,
    )


AssistantChatDep = Annotated[AssistantChat, Depends(get_assistant_chat)]


@router.post("/chats/{chat_id}/messages")
async def send_message(
    chat_id: UUID,
    message: ChatMessage,
    user: CurrentUserDep,
    chat: AssistantChatDep,
) -> EventSourceResponse:
    """Ask career-director something in one chat and stream the turn: it starts,
    thinks, writes and runs steps, then replies, asks back, fails or is stopped"""
    return EventSourceResponse(await chat.send(user.id, chat_id, message))


@router.post("/chats/{chat_id}/tasks/{task_id}/answer")
async def answer_task(
    chat_id: UUID,
    task_id: str,
    answer: Answer,
    user: CurrentUserDep,
    chat: AssistantChatDep,
) -> EventSourceResponse:
    """Answer the widget a paused turn of the chat asked, and stream the rest of it"""
    return EventSourceResponse(await chat.answer(user.id, chat_id, task_id, answer))


@router.post("/chats/{chat_id}/tasks/{task_id}/decision")
async def decide_task(
    chat_id: UUID,
    task_id: str,
    decision: ProfileDecision,
    user: CurrentUserDep,
    chat: AssistantChatDep,
) -> EventSourceResponse:
    """Approve or cancel the profile changes a paused turn of the chat proposed, and
    stream the rest of it"""
    return EventSourceResponse(await chat.decide(user.id, chat_id, task_id, decision))


@router.get("/chats/{chat_id}/stream")
async def resume_chat(
    chat_id: UUID,
    user: CurrentUserDep,
    chat: AssistantChatDep,
    last_event_id: Annotated[str | None, Header()] = None,
) -> EventSourceResponse:
    """Resume the chat's turn after the Last-Event-ID the client last saw; the turn
    kept running while the connection was down"""
    return EventSourceResponse(await chat.resume(user.id, chat_id, last_event_id))


@router.post(
    "/chats/{chat_id}/tasks/{task_id}/cancel", status_code=status.HTTP_204_NO_CONTENT
)
async def cancel_task(
    chat_id: UUID, task_id: str, user: CurrentUserDep, chat: AssistantChatDep
) -> None:
    """Stop the chat's running turn; the user's Stop button"""
    await chat.cancel(user.id, chat_id, task_id)
