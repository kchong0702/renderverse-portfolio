from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver

from src.app.a2a import Executable
from src.features import analyse_job, find_jobs
from src.shared.factory import Factory


class Container(containers.DeclarativeContainer):
    task_store = providers.Singleton(InMemoryTaskStore)
    """Where the A2A server keeps every task; swap in a database store here"""

    checkpointer = providers.Singleton(InMemorySaver)
    """Where graphs keep checkpoints so interrupted runs resume; pass it to
    each executable's graph, and swap in a database saver here"""

    job_sources = providers.Singleton(
        Factory[find_jobs.SearchProtocol], {"jsearch": find_jobs.JSearchAdapter}
    )
    """Job sources by name, each created once"""

    executables = providers.List(
        providers.Singleton(
            Executable,
            name="analyse-job",
            description="Show how well a job posting fits the user's profile, with every point cited",
            input_schema=analyse_job.AnalyseJobInput,
            graph=providers.Singleton(
                analyse_job.build_graph, checkpointer=checkpointer
            ),
        ),
        providers.Singleton(
            Executable,
            name="find-jobs",
            description="Find fresh jobs for the user's profile and preferences, ranked by fit",
            input_schema=find_jobs.FindJobsInput,
            graph=providers.Singleton(
                find_jobs.build_graph,
                checkpointer=checkpointer,
                job_sources=job_sources,
            ),
        ),
    )
    """Graphs served as A2A agents; add a feature's Executable provider here"""
