from src.features.analyse_job import JobRequirements, check_citations
from src.features.find_jobs.filters import broken_filters
from src.features.find_jobs.schemas import JobPosting, RankedJobs
from src.shared.checks import CheckError, CheckRule
from src.shared.models import Profile


def check_ranked_jobs(
    output: RankedJobs, postings: list[JobPosting], profile: Profile
) -> list[CheckError]:
    """Errors for jobs search_jobs didn't return, jobs ranked twice or breaking
    the user's preferences, and citations that don't hold for the job"""
    found = {posting.id: posting for posting in postings}
    seen: set[str] = set()
    errors: list[CheckError] = []
    for index, job in enumerate(output.jobs):
        at = f"jobs[{index}]"
        if job.job_id not in found:
            errors.append(
                CheckError(
                    rule=CheckRule.UNKNOWN_JOB,
                    at=at,
                    message=f"{job.job_id!r} is not a job search_jobs returned",
                )
            )
            continue
        if job.job_id in seen:
            errors.append(
                CheckError(
                    rule=CheckRule.DUPLICATE_JOB,
                    at=at,
                    message=f"{job.job_id!r} is ranked more than once",
                )
            )
        seen.add(job.job_id)
        if broken := broken_filters(found[job.job_id], profile.preferences):
            errors.append(
                CheckError(
                    rule=CheckRule.BREAKS_PREFERENCES,
                    at=at,
                    message=f"{job.job_id!r} breaks the user's {', '.join(broken)} preference; drop it",
                )
            )
        errors.extend(
            error.model_copy(update={"at": f"{at}.{error.at}"})
            for error in check_citations(
                JobRequirements(requirements=job.requirements),
                found[job.job_id].lines,
                profile.facts,
            )
        )
    return errors
