from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.tools import list_design_options_tool, read_pdf_lines
from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.features import write_document
from src.tools import clarify, permission, read_profile_facts


class CareerConsultantContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graphs keep checkpoints"""

    artifact_service = providers.Dependency(instance_of=ArtifactServiceClient)
    """Lists templates and prints documents"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["career-consultant"],
        tools=providers.List(
            read_pdf_lines,
            read_profile_facts,
            providers.Callable(list_design_options_tool, artifact_service),
            clarify,
            permission,
        ),
        state_schema=CareerConsultantState,
    )
    """The career-consultant agent, built once"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-consultant",
        description="Talk to career-consultant about the user's résumé or cover letter",
        graph=agent.provided.copy.call(
            update=providers.Dict(checkpointer=checkpointer)
        ),
    )
    """career-consultant served as an agent the user talks to"""

    edit_document_executable = providers.Singleton(
        Executable,
        name="edit-document",
        description="Answer the user's message about one résumé, CV or cover letter, by its id, proposing a checked changeset when an edit helps",
        reply_node="agent",
        graph=providers.Singleton(
            write_document.build_graph,
            agent=agent,
            artifact_service=artifact_service,
            checkpointer=checkpointer,
        ),
    )
    """The write-document workflow served over A2A as edit-document"""
