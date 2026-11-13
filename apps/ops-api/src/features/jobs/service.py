from __future__ import annotations

from uuid import UUID

from document_schema import DocumentKind
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import (
    Completed,
    Failed,
    InputRequired,
)
from src.core.agent_runner import AgentRunner
from src.core.exceptions import Conflict, InvalidInput, NotFound, ServiceUnavailable
from src.core.logging import get_logger
from src.db.base import utcnow
from src.features.documents import DocumentChat, DocumentService
from src.features.jobs.enums import JobStatus, Match, RunStatus, RunTrigger
from src.features.jobs.models import Job, JobRun
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import (
    AnalyseJobInput,
    AnalyseJobOutput,
    FindJobsOutput,
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
from src.features.preferences import PreferencesService
from src.features.profile import ProfileService
from src.features.settings import SettingsService

logger = get_logger(__name__)


def _tailor_request(job: JobRead, document: str) -> str:
    """The request asking edit-document to tailor a document to the job, with the
    posting's requirements and the analysis's gaps"""
    at = f" at {job.company}" if job.company else ""
    lines = [f"Tailor this {document} to the {job.title} role{at}."]
    if job.url:
        lines.append(f"The posting: {job.url}")
    if job.analysis:
        lines += ["", "The posting's requirements:"]
        lines += [
            f"- {r.text} ({r.importance.replace('_', ' ')})"
            for r in job.analysis.requirements
        ]
        gaps = [r for r in job.analysis.requirements if r.match is not Match.MET]
        if gaps:
            lines += ["", "Gaps to close where the profile supports it:"]
            lines += [
                f"- {r.text} ({r.match.replace('_', ' ')}). {r.reason}".strip()
                for r in gaps
            ]
    return "\n".join(lines)


class JobService:
    def __init__(
        self,
        session: AsyncSession,
        profile: ProfileService,
        settings: SettingsService,
        documents: DocumentService,
        chat: DocumentChat,
        runner: AgentRunner,
    ):
        """Hold the session, a repository and the preferences on it, the profile,
        settings and documents services, the document chat and the runner"""
        self._session = session
        self._repository = JobRepository(session)
        self._preferences = PreferencesService(session)
        self._profile = profile
        self._settings = settings
        self._documents = documents
        self._chat = chat
        self._runner = runner

    async def jobs(self, user_id: UUID) -> JobList:
        """Every job, best fit first, unanalysed ones last and newest first, with how
        many picks are new"""
        jobs = [
            JobRead.model_validate(job, from_attributes=True)
            for job in await self._repository.jobs(user_id)
        ]
        return JobList(
            jobs=jobs,
            new_count=sum(
                job.status == JobStatus.PICKED and job.seen_at is None for job in jobs
            ),
        )

    async def job(self, user_id: UUID, job_id: UUID) -> JobRead:
        """One of the user's jobs; NotFound when it is not theirs"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        return JobRead.model_validate(row, from_attributes=True)

    async def add(self, user_id: UUID, job: JobCreate) -> tuple[JobRead, bool]:
        """Store a posting, and whether it is new; one already stored under its
        external_id is refreshed in place and keeps its status"""
        stored = (
            await self._repository.job_at_source(user_id, job.external_id)
            if job.external_id
            else None
        )
        row = stored or Job(user_id=user_id)
        for field, value in job.model_dump(exclude={"analysis"}).items():
            setattr(row, field, value)
        row.analysis = job.analysis
        await self._repository.add(row)
        return JobRead.model_validate(row, from_attributes=True), stored is None

    async def update(self, user_id: UUID, job_id: UUID, patch: JobUpdate) -> JobRead:
        """Save, dismiss or return a job to the picks, rename one added by hand, or
        mark it opened; InvalidInput when renaming a found job"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        if (
            patch.title is not None or patch.company is not None
        ) and row.source != "manual":
            raise InvalidInput("Only a job added by hand can be renamed")
        if patch.status is not None:
            row.status = patch.status
        if patch.title is not None:
            row.title = patch.title
        if patch.company is not None:
            row.company = patch.company
        if patch.seen and row.seen_at is None:
            row.seen_at = utcnow()
        return JobRead.model_validate(row, from_attributes=True)

    async def delete(self, user_id: UUID, job_id: UUID) -> None:
        """Remove one of the user's jobs; NotFound when it is not theirs"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        await self._repository.delete(row)

    async def analyse(
        self, user_id: UUID, job_id: UUID, analysis: FitAnalysis
    ) -> JobRead:
        """Replace how a job fits the profile"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        row.analysis = analysis
        return JobRead.model_validate(row, from_attributes=True)

    async def latest_run(self, user_id: UUID) -> JobRunRead:
        """The user's most recently queued run with its status; NotFound before the
        first"""
        run = await self._repository.latest_run(user_id)
        if run is None:
            raise NotFound("The job agent has not run yet")
        return JobRunRead.model_validate(run, from_attributes=True)

    async def queue_run(
        self, user_id: UUID, trigger: RunTrigger, run: JobRunCreate
    ) -> JobRunRead:
        """Queue a run of find-jobs for a worker; Conflict while one with the same
        trigger is queued"""
        try:
            queued = await self._repository.queue_run(
                user_id, trigger, run.search, run.run_after
            )
        except IntegrityError as error:
            raise Conflict("A job agent run is already queued") from error
        return JobRunRead.model_validate(queued, from_attributes=True)

    async def find(self, user_id: UUID, search: JobSearch | None) -> JobRunRead:
        """Queue a manual run of find-jobs on the search; Conflict while a run is
        running or a manual one is queued"""
        if await self._repository.running(user_id):
            raise Conflict("The job agent is already running")
        return await self.queue_run(
            user_id, RunTrigger.MANUAL, JobRunCreate(search=search)
        )

    async def cancel_run(self, user_id: UUID, run_id: UUID) -> None:
        """Remove one of the user's queued runs; NotFound when it is not theirs,
        Conflict once a worker has taken it or it ended"""
        row = await self._repository.owned(JobRun, user_id, run_id)
        if row is None:
            raise NotFound("No such run")
        if row.status is not RunStatus.QUEUED:
            raise Conflict("The run has already started")
        await self._repository.delete(row)

    async def keep_found(self, run: JobRun, reply: FindJobsOutput) -> None:
        """Store each job find-jobs found as a pick, cut to fit or skipped when its URL
        is too long, count them on the run against min_score, and keep the quota read"""
        kept = []
        for job in reply.jobs:
            if len(job.posting.apply_url) > 2000:
                logger.warning(
                    "job_url_too_long", run_id=str(run.id), posting_id=job.posting.id
                )
            else:
                kept.append(job)
        added = [
            await self.add(
                run.user_id,
                JobCreate(
                    external_id=job.posting.id,
                    source="JSearch",
                    title=job.posting.title[:200],
                    company=job.posting.company[:200],
                    location=(
                        f"{job.posting.location}, remote"
                        if job.posting.remote
                        else job.posting.location
                    )[:200],
                    url=job.posting.apply_url,
                    posted_at=job.posting.posted_at,
                    analysis=FitAnalysis(fit=job.fit, requirements=job.requirements),
                ),
            )
            for job in kept
        ]
        min_score = (await self._preferences.get(run.user_id)).min_score
        run.found = len(added)
        run.new = sum(created for _, created in added)
        run.matched = sum(job.fit >= min_score for job in kept)
        await self._settings.record_quota(run.user_id, reply.quota)

    async def analyse_posting(
        self, user_id: UUID, job_id: UUID
    ) -> Completed[JobRead] | Failed:
        """Run analyse-job on the job's posting and the profile, and store the
        analysis in place of any earlier one"""
        job = await self.job(user_id, job_id)
        if not job.url:
            raise InvalidInput("This job has no posting URL to analyse")
        profile = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        run = await self._runner.run(
            user_id,
            "analyse-job",
            AnalyseJobOutput,
            data=AnalyseJobInput(
                url=job.url, facts=profile.facts, preferences=profile.preferences
            ),
            metadata=metadata,
        )
        match run:
            case Completed(reply=reply):
                return Completed(
                    reply=await self.analyse(user_id, job_id, reply.analysis)
                )
            case InputRequired():
                raise ServiceUnavailable("analyse-job asked for input ops cannot give")
            case Failed():
                return run

    async def tailor(self, user_id: UUID, job_id: UUID) -> TailorRead:
        """Copy the master résumé, and the master cover letter when there is one, for
        the job, then start each copy's chat turn tailoring it; Conflict without one"""
        job = await self.job(user_id, job_id)
        name = job.company or job.title
        resume = await self._documents.copy_for_job(
            user_id, job_id, DocumentKind.RESUME, f"Résumé for {name}"[:200]
        )
        if resume is None:
            raise Conflict(
                "No master résumé to tailor. Mark a résumé as master in Documents first."
            )
        letter = await self._documents.copy_for_job(
            user_id, job_id, DocumentKind.COVER_LETTER, f"Cover letter for {name}"[:200]
        )
        return TailorRead(
            resume=await self._chat.tailor(
                user_id, resume, _tailor_request(job, "résumé")
            ),
            cover_letter=await self._chat.tailor(
                user_id, letter, _tailor_request(job, "cover letter")
            )
            if letter
            else None,
        )


__all__ = ["JobService"]
