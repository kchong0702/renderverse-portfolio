from deepagents import CompiledSubAgent
from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_director import CareerDirectorState
from src.agents.career_director.tools import (
    analyse_job_tool,
    edit_document_tool,
    find_jobs_tool,
)
from src.app.a2a import Executable


class CareerDirectorContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    job_finder = providers.DependenciesContainer()
    """job-finder's container, whose agent becomes a subagent and whose workflows
    become tools"""

    career_consultant = providers.DependenciesContainer()
    """career-consultant's container, whose agent becomes a subagent and whose
    workflow becomes a tool"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["career-director"],
        tools=providers.List(
            providers.Callable(
                analyse_job_tool, job_finder.analyse_job_executable.provided.graph
            ),
            providers.Callable(
                find_jobs_tool, job_finder.find_jobs_executable.provided.graph
            ),
            providers.Callable(
                edit_document_tool,
                career_consultant.edit_document_executable.provided.graph,
            ),
        ),
        subagents=providers.List(
            providers.Singleton(
                CompiledSubAgent,
                name="job-finder",
                description="Answers questions about how jobs fit the user's profile",
                runnable=job_finder.agent,
            ),
            providers.Singleton(
                CompiledSubAgent,
                name="career-consultant",
                description="Advises on the open résumé or cover letter without changing it",
                runnable=career_consultant.agent,
            ),
        ),
        state_schema=CareerDirectorState,
    )
    """The career-director agent, built once, running the other agents as its
    subagents and the workflows as its tools"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-director",
        description="Talk to career-director from any page; it runs the other agents and workflows",
        graph=agent.provided.copy.call(
            update=providers.Dict(checkpointer=checkpointer)
        ),
    )
    """career-director served as an agent the user talks to"""
