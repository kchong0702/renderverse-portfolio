from dependency_injector import containers, providers

from src.clients.ezcareer import EzcareerClient
from src.core.auth.oauth_providers import build_providers
from src.core.config import get_settings
from src.core.runner import Runner
from src.core.stores import InMemoryRunStore, PostgresRunStore
from src.db.session import create_engine, create_session_factory


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)

    engine = providers.Singleton(create_engine, settings=settings.provided.database)

    session_factory = providers.Singleton(create_session_factory, engine=engine)

    oauth_providers = providers.Singleton(
        build_providers, settings=settings.provided.auth
    )

    ezcareer = providers.Singleton(EzcareerClient, settings=settings.provided.ezcareer)

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
