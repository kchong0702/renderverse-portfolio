from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, status

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.features.google import GoogleServiceDep
from src.features.inbox.schemas import (
    EmailCreate,
    InboxMessage,
    InboxMessageDetail,
    ReplyCreate,
)
from src.features.inbox.service import InboxService

router = APIRouter(prefix="/inbox", tags=["inbox"])


def get_inbox_service(google: GoogleServiceDep, request: Request) -> InboxService:
    """The inbox service, reading Gmail with the configured job-search query"""
    return InboxService(google, request.app.state.google, get_settings().google)


InboxServiceDep = Annotated[InboxService, Depends(get_inbox_service)]

GmailId = Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")]
"""A Gmail message or thread id"""


@router.get("")
async def list_messages(
    user: CurrentUserDep, service: InboxServiceDep
) -> list[InboxMessage]:
    """Recent job-search emails from the user's Gmail, newest first"""
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
