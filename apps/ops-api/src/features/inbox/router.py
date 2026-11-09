from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request

from src.core.auth import CurrentUserDep
from src.core.config import get_settings
from src.features.google import GoogleServiceDep
from src.features.inbox.schemas import InboxMessage, InboxMessageDetail
from src.features.inbox.service import InboxService

router = APIRouter(prefix="/inbox", tags=["inbox"])


def get_inbox_service(google: GoogleServiceDep, request: Request) -> InboxService:
    """The inbox service, reading Gmail with the configured job-search query"""
    return InboxService(
        google, request.app.state.google, get_settings().google.inbox_query
    )


InboxServiceDep = Annotated[InboxService, Depends(get_inbox_service)]


@router.get("")
async def list_messages(
    user: CurrentUserDep, service: InboxServiceDep
) -> list[InboxMessage]:
    """Recent job-search emails from the user's Gmail, newest first"""
    return await service.messages(user.id)


@router.get("/{message_id}")
async def read_message(
    message_id: Annotated[str, Path(pattern=r"^[A-Za-z0-9_-]{1,64}$")],
    user: CurrentUserDep,
    service: InboxServiceDep,
) -> InboxMessageDetail:
    """One email with its body"""
    return await service.message(user.id, message_id)
