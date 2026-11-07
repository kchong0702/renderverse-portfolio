from dependency_injector import containers, providers

from src.app.a2a import Executable
from src.features import analyse_job, find_jobs


class Container(containers.DeclarativeContainer):
    executables = providers.List(
        providers.Singleton(
            Executable,
            name="analyse-job",
            description="Show how well a job posting fits the user's profile, with every point cited",
            input_schema=analyse_job.AnalyseJobInput,
            graph=providers.Singleton(analyse_job.build_graph),
        ),
        providers.Singleton(
            Executable,
            name="find-jobs",
            description="Find fresh jobs for the user's profile and preferences, ranked by fit",
            input_schema=find_jobs.FindJobsInput,
            graph=providers.Singleton(find_jobs.build_graph),
        ),
    )
    """Graphs served as A2A agents; add a feature's Executable provider here"""
