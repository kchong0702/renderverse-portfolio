from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.middlewares import document_prompt
from src.agents.career_consultant.tools import (
    list_design_options_tool,
    propose_changeset,
    read_pdf_lines,
)
from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.features import write_document, write_networking
from src.tools import clarify, read_profile_facts


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
        response_formats=(write_networking.NetworkingCopy,),
        tools=(read_profile_facts, clarify),
        skill_tools=providers.List(
            read_pdf_lines,
            propose_changeset,
            providers.Callable(list_design_options_tool, artifact_service),
        ),
        middleware=(document_prompt,),
        state_schema=CareerConsultantState,
    )
    """The career-consultant agent, built once"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-consultant",
        description="Talk to career-consultant about the user's résumé, CV, cover letter or job portal content",
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

    write_networking_executable = providers.Singleton(
        Executable,
        name="write-networking",
        description="Write the user's job portal content from all their profile facts, to attract recruiters looking for the jobs they want: a headline, a summary and a description of each role and project, each citing its facts",
        graph=providers.Singleton(
            write_networking.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The write-networking workflow served over A2A"""
