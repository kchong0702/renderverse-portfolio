from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.applications.schemas import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationWrite,
)
from src.features.applications.service import ApplicationService
from src.features.jobs import JobServiceDep

router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_service(
    session: SessionDep, jobs: JobServiceDep
) -> ApplicationService:
    """The application service on the request's database session"""
    return ApplicationService(session, jobs)


ApplicationServiceDep = Annotated[ApplicationService, Depends(get_application_service)]


@router.get("")
async def list_applications(
    user: CurrentUserDep, service: ApplicationServiceDep
) -> list[ApplicationRead]:
    """Every application, soonest next step first"""
    return await service.applications(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_application(
    application: ApplicationCreate,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    """Track an application"""
    return await service.add(user.id, application)


@router.put("/{application_id}")
async def replace_application(
    application_id: UUID,
    application: ApplicationWrite,
    user: CurrentUserDep,
    service: ApplicationServiceDep,
) -> ApplicationRead:
    """Save every field of an application but its job"""
    return await service.replace(user.id, application_id, application)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(
    application_id: UUID, user: CurrentUserDep, service: ApplicationServiceDep
) -> None:
    """Stop tracking an application"""
    await service.delete(user.id, application_id)
