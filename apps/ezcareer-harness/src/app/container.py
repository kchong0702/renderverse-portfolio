from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver

from src.agents import build_agent, load_agents
from src.agents.job_finder import JobFinderState
from src.app.a2a import Executable
from src.core.config import get_settings
from src.features import analyse_job, find_jobs
from src.shared.factory import Factory
from src.tools import read_profile_facts


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)
    """The app's settings"""

    registry = providers.Singleton(load_agents, settings.provided.agents)
    """Every registered agent, by name"""

    task_store = providers.Singleton(InMemoryTaskStore)
    """Where the A2A server keeps every task; swap in a database store here"""

    checkpointer = providers.Singleton(InMemorySaver)
    """Where graphs keep checkpoints so interrupted runs resume; pass it to
    each executable's graph, and swap in a database saver here"""

    job_sources = providers.Singleton(
        Factory[find_jobs.SearchProtocol], {"jsearch": find_jobs.JSearchAdapter}
    )
    """Job sources by name, each created once"""

    job_finder = providers.Singleton(
        build_agent,
        agent=registry.provided["job-finder"],
        response_formats=(analyse_job.JobRequirements, find_jobs.RankedJobs),
        tools=(read_profile_facts,),
        state_schema=JobFinderState,
    )
    """The one job-finder agent the analyse-job and find-jobs workflows share"""

    analyse_job_graph = providers.Singleton(
        analyse_job.build_graph, agent=job_finder, checkpointer=checkpointer
    )
    """The analyse-job workflow"""

    find_jobs_graph = providers.Singleton(
        find_jobs.build_graph,
        agent=job_finder,
        job_sources=job_sources,
        checkpointer=checkpointer,
    )
    """The find-jobs workflow"""

    executables = providers.List(
        providers.Singleton(
            Executable,
            kind="agent",
            name="job-finder",
            description="Talk to job-finder about how jobs fit the user's profile",
            graph=job_finder,
        ),
        providers.Singleton(
            Executable,
            name="analyse-job",
            description="Show how well a job posting fits the user's profile, with every point cited",
            graph=analyse_job_graph,
        ),
        providers.Singleton(
            Executable,
            name="find-jobs",
            description="Find fresh jobs for the user's profile and preferences, ranked by fit",
            graph=find_jobs_graph,
        ),
    )
    """Agents and workflows served over A2A; add a feature's Executable provider here"""
