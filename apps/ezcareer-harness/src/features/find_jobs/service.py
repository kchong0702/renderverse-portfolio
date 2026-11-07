from src.features.find_jobs.graph import FindJobsOutput, build_graph


async def find_matching_jobs(task: object) -> FindJobsOutput:
    """Search and rank jobs for one profile with the current settings"""
    return FindJobsOutput.model_validate(await build_graph().ainvoke(task))
