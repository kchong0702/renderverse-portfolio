from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.jobs.schemas import FitAnalysis, JobCreate, JobRead, JobUpdate
from src.features.jobs.service import JobService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(session: SessionDep) -> JobService:
    """The job service on the request's database session"""
    return JobService(session)


JobServiceDep = Annotated[JobService, Depends(get_job_service)]


@router.get("")
async def list_jobs(user: CurrentUserDep, service: JobServiceDep) -> list[JobRead]:
    """Every picked, saved and dismissed job, best fit first"""
    return await service.jobs(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_job(
    job: JobCreate, user: CurrentUserDep, service: JobServiceDep
) -> JobRead:
    """Store a posting, or refresh the one stored under its external_id"""
    return await service.add(user.id, job)


@router.patch("/{job_id}")
async def update_job(
    job_id: UUID, patch: JobUpdate, user: CurrentUserDep, service: JobServiceDep
) -> JobRead:
    """Save, dismiss or return a job to the picks"""
    return await service.update(user.id, job_id, patch)


@router.put("/{job_id}/analysis")
async def replace_analysis(
    job_id: UUID, analysis: FitAnalysis, user: CurrentUserDep, service: JobServiceDep
) -> JobRead:
    """Store how a job fits the profile, replacing any earlier analysis"""
    return await service.analyse(user.id, job_id, analysis)
