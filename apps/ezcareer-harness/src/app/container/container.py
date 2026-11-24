import sys
from enum import Enum

from a2a.server.cluster import DatabaseTaskEventStream, VersionedDatabaseTaskStore
from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pydantic import BaseModel

from src.agents import load_agents
from src.app.a2a.ownership import Ownership
from src.app.container.career_consultant import CareerConsultantContainer
from src.app.container.career_director import CareerDirectorContainer
from src.app.container.clients import ClientsContainer
from src.app.container.import_document import ImportDocumentContainer
from src.app.container.job_analyst import JobAnalystContainer
from src.app.container.productivity_assistant import ProductivityAssistantContainer
from src.core.config import get_settings
from src.infrastructure.persistence import (
    MemoryTaskOwners,
    PostgresTaskOwners,
    create_engine,
    create_pool,
)


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)
    """The app's settings"""

    registry = providers.Singleton(load_agents, settings.provided.agents)
    """Every registered agent, by name"""

    engine = providers.Singleton(create_engine, settings.provided.database)
    """The SQLAlchemy engine the postgres task store, event stream and task owners
    use"""

    pool = providers.Singleton(create_pool, settings.provided.database)
    """The psycopg pool the postgres checkpointer uses"""

    task_store = providers.Selector(
        settings.provided.stores,
        memory=providers.Singleton(InMemoryTaskStore),
        postgres=providers.Singleton(VersionedDatabaseTaskStore, engine),
    )
    """Where the A2A server keeps every task, versioned in postgres so replicas
    never overwrite each other's writes"""

    event_stream = providers.Selector(
        settings.provided.stores,
        memory=providers.Object(None),
        postgres=providers.Singleton(DatabaseTaskEventStream, engine),
    )
    """The task events every replica reads, so any replica serves SubscribeToTask
    for a task another runs; None in memory, which is one process"""

    task_owners = providers.Selector(
        settings.provided.stores,
        memory=providers.Singleton(MemoryTaskOwners),
        postgres=providers.Singleton(PostgresTaskOwners, engine),
    )
    """Which process runs each running task"""

    serde = providers.Singleton(
        JsonPlusSerializer,
        allowed_msgpack_modules=providers.Callable(
            lambda: [
                value
                for name, module in [*sys.modules.items()]
                if name.partition(".")[0] in {"src", "document_schema"}
                for value in vars(module).values()
                if isinstance(value, type)
                and issubclass(value, BaseModel | Enum)
                and value.__module__ == name
            ]
        ),
    )
    """How checkpoints are written and read, rebuilding only LangGraph's safe types
    and the models and enums of the harness and document_schema"""

    checkpointer = providers.Selector(
        settings.provided.stores,
        memory=providers.Singleton(InMemorySaver, serde=serde),
        postgres=providers.Singleton(AsyncPostgresSaver, pool, serde=serde),
    )
    """Where graphs keep checkpoints, one thread per A2A context for an agent and
    per A2A task for a workflow; pass it to each executable's graph"""

    ownership = providers.Singleton(Ownership, task_owners, settings.provided.tasks)
    """Owns this process's running tasks and takes over those of dead processes"""

    clients = providers.Container(ClientsContainer, settings=settings)
    """Clients of the services the agents and workflows call"""

    job_analyst = providers.Container(
        JobAnalystContainer,
        registry=registry,
        checkpointer=checkpointer,
    )
    """job-analyst and the workflows that run on it"""

    career_consultant = providers.Container(
        CareerConsultantContainer,
        settings=settings,
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
        career_consultant.write_networking_executable,
        career_director.agent_executable,
        productivity_assistant.triage_email_executable,
        productivity_assistant.draft_reply_executable,
        import_document.import_resume_executable,
        import_document.import_profile_executable,
    )
    """Agents and workflows served over A2A; add an agent's container above and
    its Executable providers here"""
