from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from src.clients.ezcareer import Completed, Failed
from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.jobs.schemas import FitAnalysis, JobCreate, JobRead, JobUpdate
from src.features.jobs.service import JobService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    request: Request,
) -> JobService:
    """The job service on the request's database session, and the profile and
    settings services"""
    return JobService(session, profile, settings, request.app.state.ezcareer)


JobServiceDep = Annotated[JobService, Depends(get_job_service)]


@router.get("")
async def list_jobs(user: CurrentUserDep, service: JobServiceDep) -> list[JobRead]:
    """Every picked, saved and dismissed job, best fit first"""
    return await service.jobs(user.id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_job(
    job: JobCreate, user: CurrentUserDep, service: JobServiceDep, response: Response
) -> JobRead:
    """Store a new posting with 201, or refresh the one stored under its external_id
    with 200"""
    added, created = await service.add(user.id, job)
    if not created:
        response.status_code = status.HTTP_200_OK
    return added


@router.post("/find")
async def find_jobs(
    user: CurrentUserDep, service: JobServiceDep
) -> Completed[list[JobRead]] | Failed:
    """Run the job agent now: it finds fresh jobs for the profile and stores
    them as picks, or fails with its reason"""
    return await service.find(user.id)


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


@router.post("/{job_id}/analyse")
async def analyse_job(
    job_id: UUID, user: CurrentUserDep, service: JobServiceDep
) -> Completed[JobRead] | Failed:
    """Analyse the job's posting against the profile and store the analysis,
    or fail with the agent's reason"""
    return await service.analyse_posting(user.id, job_id)
