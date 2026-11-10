from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.job_finder import JobFinderState
from src.agents.job_finder.tools import search_jobs_tool
from src.app.a2a import Executable
from src.core.config import Settings
from src.features import analyse_job, find_jobs
from src.tools import read_profile_facts


class JobFinderContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    """The app's settings"""

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
        skill_tools=providers.List(
            providers.Callable(
                search_jobs_tool, job_sources, settings.provided.job_sources
            )
        ),
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
            checkpointer=checkpointer,
        ),
    )
    """The find-jobs workflow served over A2A"""
