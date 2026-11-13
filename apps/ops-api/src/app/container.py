from dependency_injector import containers, providers

from src.clients.artifact import ArtifactClient
from src.clients.ezcareer import EzcareerClient
from src.clients.google import GoogleClient
from src.clients.storage import create_storage
from src.core.auth.oauth_providers import build_providers
from src.core.config import get_settings
from src.core.data_requests import DataRequestDispatcher
from src.core.runner import Runner
from src.core.stores import InMemoryRunStore, PostgresRunStore, UsageLedger
from src.db.session import create_engine, create_session_factory
from src.features.assistant import profile_data_requests
from src.features.documents import document_data_requests
from src.features.inbox import inbox_data_requests
from src.features.jobs import job_data_requests


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

    runner = providers.Singleton(
        Runner, store=store, retry_ms=settings.provided.ezcareer.stream_retry_ms
    )

    google = providers.Singleton(GoogleClient, settings=settings.provided.google)

    storage = providers.Singleton(
        create_storage,
        settings=settings.provided.storage,
        route_prefix=settings.provided.app.route_prefix,
    )

    data_requests = providers.Singleton(
        DataRequestDispatcher,
        providers.Callable(
            inbox_data_requests,
            session_factory,
            google,
            settings.provided.google,
            ezcareer,
        ),
        providers.Callable(
            document_data_requests, session_factory, settings.provided.documents
        ),
        providers.Callable(job_data_requests, session_factory),
        providers.Callable(profile_data_requests, session_factory),
    )
