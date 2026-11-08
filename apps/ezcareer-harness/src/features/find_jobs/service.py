from src.features.find_jobs.adapters import SearchProtocol
from src.features.find_jobs.graph import FindJobsOutput, build_graph
from src.shared.factory import Factory


async def find_matching_jobs(
    task: object, job_sources: Factory[SearchProtocol]
) -> FindJobsOutput:
    """Search and rank jobs for one profile with the current settings"""
    return FindJobsOutput.model_validate(await build_graph(job_sources).ainvoke(task))
