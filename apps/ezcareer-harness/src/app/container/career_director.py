from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_director import CareerDirectorState, build_graph
from src.agents.career_director.tools import (
    analyse_job_tool,
    choose_document,
    edit_document_tool,
    find_documents,
    find_jobs_tool,
)
from src.app.a2a import Executable
from src.tools import handoff_to_child_tool


class CareerDirectorContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    job_finder = providers.DependenciesContainer()
    """job-finder's container, whose workflows become tools"""

    career_consultant = providers.DependenciesContainer()
    """career-consultant's container, whose workflow becomes a tool"""

    email_assistant = providers.DependenciesContainer()
    """email-assistant's container, whose agent the director hands email to"""

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
            providers.Callable(handoff_to_child_tool, ["email-assistant"]),
            find_documents,
            choose_document,
        ),
        state_schema=CareerDirectorState,
    )
    """The career-director agent, built once, running the workflows as its tools"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-director",
        description="Talk to career-director from any page; it runs the other agents and workflows, and hands email to email-assistant",
        graph=providers.Singleton(
            build_graph,
            director=agent,
            children=providers.List(email_assistant.agent),
            checkpointer=checkpointer,
        ),
        agent_nodes=frozenset({"career-director", "email-assistant"}),
    )
    """career-director served as an agent the user talks to, with the agents it
    hands the conversation to"""
