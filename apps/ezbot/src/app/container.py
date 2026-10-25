from dependency_injector import containers, providers

from src.app.api.fastapi.v1.services.chat import ChatService
from src.core.agent.graph import build_ezbot_graph
from src.core.config import get_settings
from src.core.rate_limit.message_limiter import MessageLimiter
from src.infrastructure.store.session import SessionStore
from src.shared.factory.classifier import create_intent_classifier
from src.shared.factory.model import create_models


class Container(containers.DeclarativeContainer):
    settings = providers.Singleton(get_settings)

    chat_models = providers.Singleton(create_models, settings=settings.provided.llm)

    intent_classifier = providers.Singleton(
        create_intent_classifier, settings=settings.provided.intent
    )

    ezbot_graph = providers.Singleton(
        build_ezbot_graph,
        models=chat_models,
        intent=settings.provided.intent,
        classifier=intent_classifier,
    )

    session_store = providers.Singleton(
        SessionStore, settings=settings.provided.session
    )

    message_limiter = providers.Singleton(
        MessageLimiter, settings=settings.provided.rate_limit
    )

    chat_service = providers.Singleton(
        ChatService,
        graph=ezbot_graph,
        chat=settings.provided.chat,
        stream=settings.provided.stream,
    )
