from __future__ import annotations

from uuid import UUID, uuid4

from document_schema import DocumentKind
from sqlalchemy.ext.asyncio import AsyncSession

from src.clients.ezcareer import Completed, EzcareerClient, Failed, InputRequired
from src.core.exceptions import Conflict, InvalidInput, NotFound, ServiceUnavailable
from src.db.base import utcnow
from src.features.documents import DocumentService
from src.features.jobs.enums import JobStatus, Match
from src.features.jobs.models import Job, JobRun
from src.features.jobs.repository import JobRepository
from src.features.jobs.schemas import (
    AnalyseJobInput,
    AnalyseJobOutput,
    FindJobsInput,
    FindJobsOutput,
    FitAnalysis,
    JobCreate,
    JobList,
    JobRead,
    JobRunRead,
    JobSearch,
    JobUpdate,
    TailorRead,
)
from src.features.profile import ProfileService
from src.features.settings import SettingsService


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
        ezcareer: EzcareerClient,
    ):
        """Hold the session to commit on and a repository on it, the profile the agents
        read, the user's model settings, the documents tailored to jobs, and the harness"""
        self._session = session
        self._repository = JobRepository(session)
        self._profile = profile
        self._settings = settings
        self._documents = documents
        self._ezcareer = ezcareer

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
        """Save, dismiss or return a job to the picks, or mark it opened"""
        row = await self._repository.owned(Job, user_id, job_id)
        if row is None:
            raise NotFound("No such job")
        if patch.status is not None:
            row.status = patch.status
        if patch.seen and row.seen_at is None:
            row.seen_at = utcnow()
        return JobRead.model_validate(row, from_attributes=True)

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
        """What the user's most recent find run found; NotFound before the first"""
        run = await self._repository.latest_run(user_id)
        if run is None:
            raise NotFound("The job agent has not run yet")
        return JobRunRead.model_validate(run, from_attributes=True)

    async def find(
        self, user_id: UUID, search: JobSearch | None
    ) -> Completed[list[JobRead]] | Failed:
        """Run find-jobs on the profile and the search, store each job it found as a
        pick with its analysis, and record the run's counts"""
        profile = await self._profile.agent_profile(user_id)
        metadata = await self._settings.run_metadata(user_id)
        await self._session.commit()
        run = await self._ezcareer.send(
            "find-jobs",
            FindJobsOutput,
            user_id=user_id,
            context_id=f"{user_id}:{uuid4()}",
            data=FindJobsInput(
                facts=profile.facts, preferences=profile.preferences, search=search
            ),
            metadata=metadata,
        )
        match run:
            case Completed(reply=reply):
                added = [
                    await self.add(
                        user_id,
                        JobCreate(
                            external_id=job.posting.id,
                            source="JSearch",
                            title=job.posting.title,
                            company=job.posting.company,
                            location=f"{job.posting.location}, remote"
                            if job.posting.remote
                            else job.posting.location,
                            url=job.posting.apply_url,
                            posted_at=job.posting.posted_at,
                            analysis=FitAnalysis(
                                fit=job.fit, requirements=job.requirements
                            ),
                        ),
                    )
                    for job in reply.jobs
                ]
                await self._repository.add(
                    JobRun(
                        user_id=user_id,
                        found=len(added),
                        new=sum(created for _, created in added),
                        scored_70=sum(job.fit >= 70 for job in reply.jobs),
                    )
                )
                await self._settings.record_quota(user_id, reply.quota)
                return Completed(reply=[job for job, _ in added])
            case InputRequired():
                raise ServiceUnavailable("find-jobs asked for input ops cannot give")
            case Failed():
                return run

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
        run = await self._ezcareer.send(
            "analyse-job",
            AnalyseJobOutput,
            user_id=user_id,
            context_id=f"{user_id}:{uuid4()}",
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
            resume=await self._documents.tailor(
                user_id, resume, _tailor_request(job, "résumé")
            ),
            cover_letter=await self._documents.tailor(
                user_id, letter, _tailor_request(job, "cover letter")
            )
            if letter
            else None,
        )


__all__ = ["JobService"]
