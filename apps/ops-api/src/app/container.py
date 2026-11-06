from dependency_injector import containers, providers

from src.core.auth.oauth_providers import build_providers
from src.core.config import get_settings
from src.core.db.session import create_engine, create_session_factory


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)

    engine = providers.Singleton(create_engine, settings=settings.provided.database)

    session_factory = providers.Singleton(create_session_factory, engine=engine)

    oauth_providers = providers.Singleton(
        build_providers, settings=settings.provided.auth
    )
