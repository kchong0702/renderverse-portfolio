from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, status
from fastapi.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Answer, SummaryUpdate, ThreadSummary
from src.core.agent_runner import Turn
from src.core.auth.dependencies import current_timezone, current_user
from src.core.auth.models import User
from src.core.stores import RunRecord
from src.db.session import get_session
from src.features.assistant.schemas import ProfileDecision
from src.features.conversations.enums import ServedAgent
from src.features.conversations.schemas import MessagePage, MessageSend, SessionRead
from src.features.conversations.service import ConversationService
from src.features.conversations.turns import ConversationTurns
from src.features.documents import document_service
from src.features.profile import ProfileService
from src.features.settings import settings_service

if TYPE_CHECKING:
    from src.app.container import Container


router = APIRouter(prefix="/agent", tags=["agent"])


def conversation_service(
    session: AsyncSession, container: "Container"
) -> ConversationService:
    """The conversation service on the session, its runner from the container"""
    return ConversationService(
        session,
        ConversationTurns(container.session_factory(), container.runner()),
        container.runner(),
        document_service(session, container),
        ProfileService(session),
        settings_service(session, container),
    )


async def recovered_turn(container: "Container", run: RunRecord) -> Turn:
    """The turn a run left running by a stopped process belongs to"""
    async with container.session_factory()() as session:
        metadata = await settings_service(session, container).run_metadata(run.user_id)
    return ConversationTurns(container.session_factory(), container.runner()).turn(
        run.user_id, UUID(run.thread_id), ServedAgent(run.agent), metadata
    )


def get_conversation_service(
    session: Annotated[AsyncSession, Depends(get_session, scope="function")],
    request: Request,
) -> ConversationService:
    """The conversation service on the request's database session"""
    return conversation_service(session, request.app.state.container)


@router.get("/sessions/{agent}")
async def read_session(
    agent: ServedAgent,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    document_id: UUID | None = None,
) -> SessionRead:
    """The user's conversation with the agent and its active thread; career-consultant
    keeps one per document_id, which it requires and career-director refuses"""
    return await service.session(user.id, agent, document_id)


@router.post("/sessions/{agent}/threads", status_code=status.HTTP_201_CREATED)
async def clear_conversation(
    agent: ServedAgent,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    document_id: UUID | None = None,
) -> SessionRead:
    """Clear the conversation, career-consultant's on document_id: new turns go on a
    new thread"""
    return await service.clear(user.id, agent, document_id)


@router.get("/threads/{thread_id}/messages")
async def list_messages(
    thread_id: UUID,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    before: str | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> MessagePage:
    """A page of the thread's messages before `before`, or its latest, oldest
    first"""
    return await service.messages(user.id, thread_id, before, limit)


@router.post("/threads/{thread_id}/messages")
async def send_message(
    thread_id: UUID,
    message: MessageSend,
    user: Annotated[User, Depends(current_user)],
    timezone: Annotated[str, Depends(current_timezone)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> EventSourceResponse:
    """Send the thread's agent a message and stream the turn: it starts, thinks,
    writes and runs steps, then replies, asks back, fails or is stopped"""
    return EventSourceResponse(
        await service.send(user.id, thread_id, message.text, timezone)
    )


@router.post("/threads/{thread_id}/tasks/{task_id}/answer")
async def answer_task(
    thread_id: UUID,
    task_id: str,
    answer: Answer,
    user: Annotated[User, Depends(current_user)],
    timezone: Annotated[str, Depends(current_timezone)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> EventSourceResponse:
    """Answer the widget a paused turn asked, and stream the rest of it"""
    return EventSourceResponse(
        await service.answer(
            user.id,
            thread_id,
            task_id,
            answer,
            answer.input or ("Submitted" if answer.accept else "Cancelled"),
            timezone,
        )
    )


@router.post("/threads/{thread_id}/tasks/{task_id}/decision")
async def decide_task(
    thread_id: UUID,
    task_id: str,
    decision: ProfileDecision,
    user: Annotated[User, Depends(current_user)],
    timezone: Annotated[str, Depends(current_timezone)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> EventSourceResponse:
    """Approve or cancel the profile changes a paused turn proposed, and stream the
    rest of it"""
    return EventSourceResponse(
        await service.decide(user.id, thread_id, task_id, decision, timezone)
    )


@router.get("/threads/{thread_id}/stream")
async def resume_turn(
    thread_id: UUID,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
    last_event_id: Annotated[str | None, Header()] = None,
) -> EventSourceResponse:
    """Resume the thread's turn after the Last-Event-ID the client last saw; the
    turn kept running while the connection was down"""
    return EventSourceResponse(await service.resume(user.id, thread_id, last_event_id))


@router.delete(
    "/threads/{thread_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def stop_task(
    thread_id: UUID,
    task_id: str,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> None:
    """Stop the thread's running turn; the user's Stop button"""
    await service.cancel(user.id, thread_id, task_id)


@router.get("/threads/{thread_id}/summary")
async def read_summary(
    thread_id: UUID,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ThreadSummary:
    """What the thread's agent remembers of its earlier messages"""
    return await service.summary(user.id, thread_id)


@router.put("/threads/{thread_id}/summary")
async def update_summary(
    thread_id: UUID,
    update: SummaryUpdate,
    user: Annotated[User, Depends(current_user)],
    service: Annotated[ConversationService, Depends(get_conversation_service)],
) -> ThreadSummary:
    """Replace what the agent remembers of the thread with the user's edit"""
    return await service.update_summary(user.id, thread_id, update)


__all__ = ["conversation_service", "recovered_turn", "router"]
