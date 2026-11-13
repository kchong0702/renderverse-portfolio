from src.features.find_jobs.schemas import JobPosting, MatchedJob, RankedJobs
from src.shared.jobs import job_key


def matched_jobs(output: RankedJobs, postings: list[JobPosting]) -> list[MatchedJob]:
    """Join each ranked job with its posting, highest fit first.
    Ties keep the agent's order."""
    found = {job_key(posting.id): posting for posting in postings}
    matched = [
        MatchedJob(posting=found[job.job_id], requirements=job.requirements)
        for job in output.jobs
    ]
    return sorted(matched, key=lambda job: job.fit, reverse=True)
