from dependency_injector import containers, providers

from src.adapters.job_sources import build_job_source
from src.adapters.oauth_providers import build_providers
from src.adapters.storage import create_storage
from src.clients.artifact import ArtifactClient
from src.clients.ezcareer import EzcareerClient
from src.clients.google import GoogleClient
from src.core.agent_runner import AgentRunner, ToolExecutor
from src.core.config import get_settings
from src.core.stores import InMemoryRunStore, PostgresRunStore, UsageLedger
from src.db.session import create_engine, create_session_factory
from src.features.assistant import profile_tools
from src.features.documents import document_tools
from src.features.inbox import inbox_tools
from src.features.jobs import job_tools


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)

    artifact = providers.Singleton(ArtifactClient, settings=settings.provided.artifact)

    engine = providers.Singleton(create_engine, settings=settings.provided.database)

    session_factory = providers.Singleton(create_session_factory, engine=engine)

    oauth_providers = providers.Singleton(
        build_providers, settings=settings.provided.auth
    )

    ledger = providers.Singleton(
        UsageLedger,
        session_factory=session_factory,
        settings=settings.provided.ezcareer,
    )

    ezcareer = providers.Singleton(
        EzcareerClient,
        settings=settings.provided.ezcareer,
        record_usage=ledger.provided.record,
    )

    store = providers.Selector(
        settings.provided.ezcareer.stores,
        memory=providers.Singleton(
            InMemoryRunStore, settings=settings.provided.ezcareer
        ),
        postgres=providers.Singleton(
            PostgresRunStore,
            session_factory=session_factory,
            database=settings.provided.database,
            settings=settings.provided.ezcareer,
        ),
    )

    google = providers.Singleton(GoogleClient, settings=settings.provided.google)

    job_source = providers.Singleton(
        build_job_source,
        source=settings.provided.jobs.source,
        jsearch=settings.provided.jsearch,
    )

    storage = providers.Singleton(
        create_storage,
        settings=settings.provided.storage,
        route_prefix=settings.provided.app.route_prefix,
    )

    tools = providers.Singleton(
        ToolExecutor,
        providers.List(
            providers.Callable(
                inbox_tools,
                session_factory,
                google,
                settings.provided.google,
            ),
            providers.Callable(
                document_tools, session_factory, settings.provided.documents
            ),
            providers.Callable(job_tools, session_factory, job_source),
            providers.Callable(profile_tools, session_factory),
        ),
    )

    runner = providers.Singleton(
        AgentRunner,
        ezcareer=ezcareer,
        tools=tools,
        store=store,
        retry_ms=settings.provided.ezcareer.stream_retry_ms,
    )
