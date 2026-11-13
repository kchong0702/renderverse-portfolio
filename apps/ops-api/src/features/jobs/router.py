from typing import TYPE_CHECKING, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import CurrentUserDep
from src.core.exceptions import InvalidInput
from src.db.session import SessionDep
from src.features.documents import document_chat, document_service
from src.features.jobs.enums import RunTrigger
from src.features.jobs.schemas import (
    FitAnalysis,
    JobCreate,
    JobList,
    JobRead,
    JobRunCreate,
    JobRunRead,
    JobSearch,
    JobUpdate,
    TailorRead,
)
from src.features.jobs.service import JobService
from src.features.profile import ProfileService
from src.features.settings import settings_service

if TYPE_CHECKING:
    from src.app.container import Container


router = APIRouter(prefix="/jobs", tags=["jobs"])


def job_service(session: AsyncSession, container: "Container") -> JobService:
    """The job service on the session, its clients from the container"""
    return JobService(
        session,
        ProfileService(session),
        settings_service(session, container),
        document_service(session, container),
        document_chat(session, container),
        container.runner(),
    )


def get_job_service(session: SessionDep, request: Request) -> JobService:
    """The job service on the request's database session"""
    return job_service(session, request.app.state.container)


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
    with 200; 422 for the manual source"""
    if job.source == "manual":
        raise InvalidInput("The manual source is kept for jobs tracked by hand")
    added, created = await service.add(user.id, job)
    if not created:
        response.status_code = status.HTTP_200_OK
    return added


@router.post("/find", status_code=status.HTTP_202_ACCEPTED)
async def find_jobs(
    user: CurrentUserDep, service: JobServiceDep, search: JobSearch | None = None
) -> JobRunRead:
    """Queue a run of the job agent on the search when sent, which a worker runs to
    store fresh jobs as picks; 409 while a run is running or a manual one is queued"""
    return await service.find(user.id, search)


@router.post("/runs", status_code=status.HTTP_202_ACCEPTED)
async def queue_run(
    run: JobRunCreate, user: CurrentUserDep, service: JobServiceDep
) -> JobRunRead:
    """Queue a run of the job agent for the assistant, now or after run_after; 409
    while an agent run is queued"""
    return await service.queue_run(user.id, RunTrigger.AGENT, run)


@router.get("/runs/latest")
async def latest_run(user: CurrentUserDep, service: JobServiceDep) -> JobRunRead:
    """The job agent's most recent run with its status and what it found, or 404
    before its first"""
    return await service.latest_run(user.id)


@router.delete("/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_run(
    run_id: UUID, user: CurrentUserDep, service: JobServiceDep
) -> None:
    """Cancel a queued run; 409 once a worker has taken it or it ended"""
    await service.cancel_run(user.id, run_id)


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
) -> JobRead:
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
