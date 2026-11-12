from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status

from src.clients.ezcareer import Failed
from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.applications.schemas import (
    ApplicationRead,
    ApplicationUpdate,
    JobApplicationCreate,
    ManualApplicationCreate,
)
from src.features.applications.service import ApplicationService
from src.features.inbox import InboxServiceDep
from src.features.inbox.schemas import FollowUpDraft
from src.features.jobs.router import job_service

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(
    session: SessionDep, request: Request
) -> ApplicationService:
    """The application service on the request's database session"""
    return ApplicationService(
        session, job_service(session, request.app.state.container)
    )


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]


@router.get("")
async def list_applications(
    user: CurrentUserDep, service: ApplicationServiceDep
) -> list[ApplicationRead]:
    """Every application, soonest next step first"""
    return await service.applications(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_application(
    application: JobApplicationCreate | ManualApplicationCreate,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    """Track an application for a stored job, or for a new saved job made from the
    company and role; 409 when the job has one already"""
    return await service.add(user.id, application)


@router.put("/{application_id}")
async def replace_application(
    application_id: UUID,
    application: ApplicationUpdate,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    """Save every field of an application, and its job's company and role"""
    return await service.replace(user.id, application_id, application)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: UUID, user: CurrentUserDep, service: ApplicationServiceDep
) -> None:
    """Stop tracking an application, and delete its job when it was tracked by
    hand"""
    await service.delete(user.id, application_id)


@router.post("/{application_id}/follow-up-draft")
async def draft_follow_up(
    application_id: UUID, user: CurrentUserDep, inbox: InboxServiceDep
) -> FollowUpDraft | Failed:
    """Draft a follow-up email for an application with no reply, or fail with the
    agent's reason; nothing is sent"""
    return await inbox.draft_follow_up(user.id, application_id)
