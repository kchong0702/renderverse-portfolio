from src.features.analyse_job import JobRequirements, check_citations
from src.features.find_jobs.schemas import JobPosting, RankedJobs
from src.shared.checks import CheckError
from src.shared.models import ProfileFact


def check_ranked_jobs(
    output: RankedJobs, postings: list[JobPosting], facts: list[ProfileFact]
) -> list[CheckError]:
    """Errors for jobs search_jobs didn't return, jobs ranked twice, and
    requirement citations that don't hold for the job's description"""
    found = {posting.id: posting for posting in postings}
    seen: set[str] = set()
    errors: list[CheckError] = []
    for index, job in enumerate(output.jobs):
        at = f"jobs[{index}]"
        if job.job_id not in found:
            errors.append(
                CheckError(
                    rule="unknown_job",
                    at=at,
                    message=f"{job.job_id!r} is not a job search_jobs returned",
                )
            )
            continue
        if job.job_id in seen:
            errors.append(
                CheckError(
                    rule="duplicate_job",
                    at=at,
                    message=f"{job.job_id!r} is ranked more than once",
                )
            )
        seen.add(job.job_id)
        errors.extend(
            error.model_copy(update={"at": f"{at}.{error.at}"})
            for error in check_citations(
                JobRequirements(requirements=job.requirements),
                found[job.job_id].lines,
                facts,
            )
        )
    return errors
