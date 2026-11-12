from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_director import CareerDirectorState, build_graph
from src.agents.career_director.tools import (
    analyse_job_tool,
    choose_document,
    edit_document_tool,
    find_documents,
    find_jobs_tool,
    preview_profile_sync,
    schedule_job_run,
    update_profile,
)
from src.app.a2a import Executable
from src.tools import handoff_to_child_tool, read_profile_facts


class CareerDirectorContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    job_analyst = providers.DependenciesContainer()
    """job-analyst's container, whose workflows become tools"""

    career_consultant = providers.DependenciesContainer()
    """career-consultant's container, whose workflow becomes a tool"""

    productivity_assistant = providers.DependenciesContainer()
    """productivity-assistant's container, whose agent the director hands email to"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["career-director"],
        tools=providers.List(
            providers.Callable(
                analyse_job_tool, job_analyst.analyse_job_executable.provided.graph
            ),
            providers.Callable(
                find_jobs_tool, job_analyst.find_jobs_executable.provided.graph
            ),
            providers.Callable(
                edit_document_tool,
                career_consultant.edit_document_executable.provided.graph,
            ),
            providers.Callable(handoff_to_child_tool, ["productivity-assistant"]),
            find_documents,
            choose_document,
            schedule_job_run,
            read_profile_facts,
        ),
        skill_tools=(preview_profile_sync, update_profile),
        state_schema=CareerDirectorState,
        interrupt_on={"update_profile": {"allowed_decisions": ["approve", "reject"]}},
    )
    """The career-director agent, built once, running the workflows as its tools and
    saving profile changes only once the user approves them"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-director",
        description="Talk to career-director from any page; it edits documents and analyses and finds jobs through workflows, queues background job runs, updates the profile once the user approves, and hands email to productivity-assistant",
        graph=providers.Singleton(
            build_graph,
            director=agent,
            children=providers.List(productivity_assistant.agent),
            checkpointer=checkpointer,
        ),
        agent_nodes=frozenset({"career-director", "productivity-assistant"}),
    )
    """career-director served as an agent the user talks to, with the agents it
    hands the conversation to"""
