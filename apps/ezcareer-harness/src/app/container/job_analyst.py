from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.job_analyst import JobAnalystState
from src.agents.job_analyst.tools import search_jobs
from src.app.a2a import Executable
from src.features import analyse_job, find_jobs
from src.tools import read_profile_facts


class JobAnalystContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graphs keep checkpoints"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["job-analyst"],
        response_formats=(analyse_job.JobRequirements, find_jobs.RankedJobs),
        tools=(read_profile_facts,),
        skill_tools=(search_jobs,),
        state_schema=JobAnalystState,
    )
    """The job-analyst agent, built once"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="job-analyst",
        description="Talk to job-analyst about how jobs fit the user's profile",
        graph=agent.provided.copy.call(
            update=providers.Dict(checkpointer=checkpointer)
        ),
    )
    """job-analyst served as an agent the user talks to"""

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
