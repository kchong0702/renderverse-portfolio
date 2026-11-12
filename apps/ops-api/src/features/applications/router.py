from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from pydantic import AwareDatetime

from src.clients.ezcareer import Failed
from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.applications.schemas import (
    ApplicationRead,
    ApplicationUpdate,
    JobApplicationCreate,
    ManualApplicationCreate,
    StepRead,
    StepWrite,
)
from src.features.applications.service import ApplicationService
from src.features.inbox import InboxServiceDep
from src.features.inbox.schemas import FollowUpDraft
from src.features.jobs.router import job_service
from src.features.settings import settings_service

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(
    session: SessionDep, request: Request
) -> ApplicationService:
    """The application service on the request's database session"""
    container = request.app.state.container
    return ApplicationService(
        session,
        job_service(session, container),
        settings_service(session, container),
    )


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]


@router.get("")
async def list_applications(
    user: CurrentUserDep, service: ApplicationServiceDep
) -> list[ApplicationRead]:
    """Every application: overdue ones first, then soonest next step first"""
    return await service.applications(user.id)


@router.get("/steps")
async def list_steps_between(
    start: AwareDatetime,
    end: AwareDatetime,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> list[StepRead]:
    """The user's steps that start from start until end, soonest first"""
    return await service.steps_between(user.id, start, end)


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


@router.get("/{application_id}/steps")
async def list_steps(
    application_id: UUID, user: CurrentUserDep, service: ApplicationServiceDep
) -> list[StepRead]:
    """The application's steps, soonest first"""
    return await service.steps(user.id, application_id)


@router.post("/{application_id}/steps", status_code=status.HTTP_201_CREATED)
async def add_step(
    application_id: UUID,
    step: StepWrite,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> StepRead:
    """Add an interview, follow-up, take-home or offer deadline to the application"""
    return await service.add_step(user.id, application_id, step)


@router.put("/{application_id}/steps/{step_id}")
async def replace_step(
    application_id: UUID,
    step_id: UUID,
    step: StepWrite,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> StepRead:
    """Save every field of a step, such as a new time or done"""
    return await service.replace_step(user.id, application_id, step_id, step)


@router.delete(
    "/{application_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_step(
    application_id: UUID,
    step_id: UUID,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> None:
    """Remove a step"""
    await service.delete_step(user.id, application_id, step_id)


@router.post("/{application_id}/follow-up-draft")
async def draft_follow_up(
    application_id: UUID, user: CurrentUserDep, inbox: InboxServiceDep
) -> FollowUpDraft | Failed:
    """Draft a follow-up email for an application with no reply, or fail with the
    agent's reason; nothing is sent"""
    return await inbox.draft_follow_up(user.id, application_id)
