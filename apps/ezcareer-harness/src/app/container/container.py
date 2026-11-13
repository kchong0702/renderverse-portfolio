from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver

from src.agents import load_agents
from src.app.container.career_consultant import CareerConsultantContainer
from src.app.container.career_director import CareerDirectorContainer
from src.app.container.clients import ClientsContainer
from src.app.container.import_document import ImportDocumentContainer
from src.app.container.job_analyst import JobAnalystContainer
from src.app.container.productivity_assistant import ProductivityAssistantContainer
from src.core.config import get_settings


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)
    """The app's settings"""

    registry = providers.Singleton(load_agents, settings.provided.agents)
    """Every registered agent, by name"""

    task_store = providers.Singleton(InMemoryTaskStore)
    """Where the A2A server keeps every task; swap in a database store here"""

    checkpointer = providers.Singleton(InMemorySaver)
    """Where graphs keep checkpoints so interrupted runs resume; pass it to
    each executable's graph, and swap in a database saver here"""

    clients = providers.Container(ClientsContainer, settings=settings)
    """Clients of the services the agents and workflows call"""

    job_analyst = providers.Container(
        JobAnalystContainer,
        settings=settings,
        registry=registry,
        checkpointer=checkpointer,
        job_sources=clients.job_sources,
    )
    """job-analyst and the workflows that run on it"""

    career_consultant = providers.Container(
        CareerConsultantContainer,
        registry=registry,
        checkpointer=checkpointer,
        artifact_service=clients.artifact_service,
    )
    """career-consultant and the workflows that run on it"""

    productivity_assistant = providers.Container(
        ProductivityAssistantContainer,
        settings=settings,
        registry=registry,
        checkpointer=checkpointer,
    )
    """productivity-assistant and the email workflows that run on it"""

    career_director = providers.Container(
        CareerDirectorContainer,
        registry=registry,
        checkpointer=checkpointer,
        job_analyst=job_analyst,
        career_consultant=career_consultant,
        productivity_assistant=productivity_assistant,
    )
    """career-director, which runs the workflows as its tools"""

    import_document = providers.Container(
        ImportDocumentContainer,
        registry=registry,
        checkpointer=checkpointer,
        artifact_service=clients.artifact_service,
    )
    """The import-resume and import-profile workflows, which turn an uploaded résumé
    into a draft and a profile export into profile facts"""

    executables = providers.List(
        job_analyst.agent_executable,
        job_analyst.analyse_job_executable,
        job_analyst.find_jobs_executable,
        career_consultant.agent_executable,
        career_consultant.edit_document_executable,
        career_consultant.write_networking_executable,
        career_director.agent_executable,
        productivity_assistant.triage_email_executable,
        productivity_assistant.draft_reply_executable,
        import_document.import_resume_executable,
        import_document.import_profile_executable,
    )
    """Agents and workflows served over A2A; add an agent's container above and
    its Executable providers here"""
