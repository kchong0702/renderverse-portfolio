from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status

from src.clients.ezcareer import Completed, Failed
from src.core.auth import CurrentUserDep
from src.db.session import SessionDep
from src.features.documents import DocumentServiceDep
from src.features.jobs.schemas import (
    FitAnalysis,
    JobCreate,
    JobList,
    JobRead,
    JobRunRead,
    JobSearch,
    JobUpdate,
    TailorRead,
)
from src.features.jobs.service import JobService
from src.features.profile import ProfileServiceDep
from src.features.settings import SettingsServiceDep

router = APIRouter(prefix="/jobs", tags=["jobs"])


def get_job_service(
    session: SessionDep,
    profile: ProfileServiceDep,
    settings: SettingsServiceDep,
    documents: DocumentServiceDep,
    request: Request,
) -> JobService:
    """The job service on the request's database session, and the profile,
    settings and documents services"""
    return JobService(session, profile, settings, documents, request.app.state.ezcareer)


JobServiceDep = Annotated[JobService, Depends(get_job_service)]


@router.get("")
async def list_jobs(user: CurrentUserDep, service: JobServiceDep) -> JobList:
    """Every picked, saved and dismissed job, best fit first, and how many picks
    are new"""
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
    user: CurrentUserDep, service: JobServiceDep, search: JobSearch | None = None
) -> Completed[list[JobRead]] | Failed:
    """Run the job agent now, on the search when sent: it finds fresh jobs for the
    profile and stores them as picks, or fails with its reason"""
    return await service.find(user.id, search)


@router.get("/runs/latest")
async def latest_run(user: CurrentUserDep, service: JobServiceDep) -> JobRunRead:
    """What the job agent's most recent run found, or 404 before its first"""
    return await service.latest_run(user.id)


@router.patch("/{job_id}")
async def update_job(
    job_id: UUID, patch: JobUpdate, user: CurrentUserDep, service: JobServiceDep
) -> JobRead:
    """Save, dismiss or return a job to the picks, or mark it opened"""
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


@router.post("/{job_id}/tailor")
async def tailor_documents(
    job_id: UUID, user: CurrentUserDep, service: JobServiceDep
) -> TailorRead:
    """Tailor the master résumé and cover letter to the job: each is copied once
    and edit-document's changeset waits for review in Documents"""
    return await service.tailor(user.id, job_id)
