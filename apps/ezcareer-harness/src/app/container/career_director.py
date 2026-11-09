from deepagents import CompiledSubAgent
from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_director import CareerDirectorState, workflow_runnable
from src.app.a2a import Executable


class CareerDirectorContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    job_finder = providers.DependenciesContainer()
    """job-finder's container, whose agent and workflows become subagents"""

    career_consultant = providers.DependenciesContainer()
    """career-consultant's container, whose agent and workflow become subagents"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["career-director"],
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
            providers.Singleton(
                CompiledSubAgent,
                name="analyse-job",
                description="Shows how well the job posting at a URL fits the user's profile, with every point cited",
                runnable=providers.Singleton(
                    workflow_runnable,
                    job_finder.analyse_job_executable.provided.graph,
                    "url",
                ),
            ),
            providers.Singleton(
                CompiledSubAgent,
                name="find-jobs",
                description="Finds fresh jobs for the user's profile and preferences, ranked by fit",
                runnable=providers.Singleton(
                    workflow_runnable, job_finder.find_jobs_executable.provided.graph
                ),
            ),
            providers.Singleton(
                CompiledSubAgent,
                name="edit-document",
                description="Proposes a checked changeset for a change to the open résumé or cover letter",
                runnable=providers.Singleton(
                    workflow_runnable,
                    career_consultant.edit_document_executable.provided.graph,
                ),
            ),
        ),
        state_schema=CareerDirectorState,
    )
    """The career-director agent, built once, running the other agents and
    workflows as its subagents"""

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
