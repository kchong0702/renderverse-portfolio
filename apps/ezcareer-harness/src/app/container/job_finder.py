from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.job_finder import JobFinderState
from src.app.a2a import Executable
from src.features import analyse_job, find_jobs
from src.tools import read_profile_facts


class JobFinderContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graphs keep checkpoints"""

    job_sources = providers.Dependency()
    """Job sources by name"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["job-finder"],
        response_formats=(analyse_job.JobRequirements, find_jobs.RankedJobs),
        tools=(read_profile_facts,),
        state_schema=JobFinderState,
    )
    """The job-finder agent, built once"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="job-finder",
        description="Talk to job-finder about how jobs fit the user's profile",
        graph=agent.provided.copy.call(
            update=providers.Dict(checkpointer=checkpointer)
        ),
    )
    """job-finder served as an agent the user talks to"""

    analyse_job_executable = providers.Singleton(
        Executable,
        name="analyse-job",
        description="Show how well a job posting fits the user's profile, with every point cited",
        graph=providers.Singleton(
            analyse_job.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The analyse-job workflow served over A2A"""

    find_jobs_executable = providers.Singleton(
        Executable,
        name="find-jobs",
        description="Find fresh jobs for the user's profile and preferences, ranked by fit",
        graph=providers.Singleton(
            find_jobs.build_graph,
            agent=agent,
            job_sources=job_sources,
            checkpointer=checkpointer,
        ),
    )
    """The find-jobs workflow served over A2A"""
