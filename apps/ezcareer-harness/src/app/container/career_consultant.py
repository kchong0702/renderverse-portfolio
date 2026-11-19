from dependency_injector import containers, providers

from src.agents import build_agent
from src.agents.career_consultant import CareerConsultantState
from src.agents.career_consultant.middlewares import document_prompt, load_document
from src.agents.career_consultant.tools import (
    list_design_options_tool,
    propose_changeset_tool,
    read_pdf_lines,
)
from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import Settings
from src.features import write_networking
from src.tools import clarify, read_profile_facts


class CareerConsultantContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    """The app's settings"""

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
            providers.Callable(
                propose_changeset_tool,
                artifact_service,
                settings.provided.documents.page_fit_trims,
            ),
            providers.Callable(list_design_options_tool, artifact_service),
        ),
        middleware=(load_document, document_prompt),
        state_schema=CareerConsultantState,
    )
    """The career-consultant agent, built once"""

    agent_executable = providers.Singleton(
        Executable,
        kind="agent",
        name="career-consultant",
        description="Talk to career-consultant about one of the user's résumés, CVs or cover letters, by its document_id, which it loads and proposes checked edits to",
        graph=agent.provided.copy.call(
            update=providers.Dict(checkpointer=checkpointer)
        ).provided.with_config.call(
            recursion_limit=settings.provided.documents.recursion_limit
        ),
    )
    """career-consultant served as an agent the user talks to, each turn stopped
    after [documents] recursion_limit steps"""

    write_networking_executable = providers.Singleton(
        Executable,
        name="write-networking",
        description="Write the user's job portal content from all their profile facts, to attract recruiters looking for the jobs they want: a headline, a summary and a description of each role and project, each citing its facts",
        graph=providers.Singleton(
            write_networking.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The write-networking workflow served over A2A"""
