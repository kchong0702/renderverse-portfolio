from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.db.session import SessionDep
from src.features.calendar import CalendarServiceDep
from src.features.google import GoogleServiceDep
from src.features.inbox.schemas import (
    DraftReplyOutput,
    EmailCreate,
    InboxList,
    InboxMessageDetail,
    ReplyCreate,
)
from src.features.inbox.service import InboxService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/inbox", tags=["inbox"])


def get_inbox_service(
    session: SessionDep,
    google: GoogleServiceDep,
    settings: SettingsServiceDep,
    calendar: CalendarServiceDep,
    profile: ProfileServiceDep,
    request: Request,
) -> InboxService:
    """The inbox service on the request's database session, with Gmail, Calendar,
    the user's settings and profile, and the agent runner"""
    return InboxService(
        session,
        google,
        settings,
        calendar,
        profile,
        request.app.state.google,
        request.app.state.runner,
        get_settings().google,
    )


InboxServiceDep = Annotated[InboxService, Depends(get_inbox_service)]

GmailId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""A Gmail message or thread id"""


@router.get("")
async def list_messages(user: CurrentUserDep, service: InboxServiceDep) -> InboxList:
    """Recent job-search emails from the user's Gmail, newest first, with what each
    thread needs; new or changed threads are triaged first"""
    return await service.messages(user.id)


@router.post("/compose", status_code=status.HTTP_204_NO_CONTENT)
async def send_email(
    email: EmailCreate, user: CurrentUserDep, service: InboxServiceDep
) -> None:
    """Send a new email from the user's Gmail"""
    await service.send(user.id, email)


@router.get("/{message_id}")
async def read_message(
    message_id: GmailId,
    user: CurrentUserDep,
    service: InboxServiceDep,
) -> InboxMessageDetail:
    """One email with its body"""
    return await service.message(user.id, message_id)


@router.post("/{thread_id}/reply", status_code=status.HTTP_204_NO_CONTENT)
async def send_reply(
    thread_id: GmailId,
    reply: ReplyCreate,
    user: CurrentUserDep,
    service: InboxServiceDep,
) -> None:
    """Send the reply in the Gmail thread to the last person other than the user
    who wrote in it"""
    await service.reply(user.id, thread_id, reply)


@router.post("/{thread_id}/reply-draft")
async def draft_reply(
    thread_id: GmailId, user: CurrentUserDep, service: InboxServiceDep
) -> DraftReplyOutput:
    """Draft a reply to the thread, offering free calendar slots while the user lets
    it, or fail with the agent's reason; nothing is sent"""
    return await service.draft_reply(user.id, thread_id)
