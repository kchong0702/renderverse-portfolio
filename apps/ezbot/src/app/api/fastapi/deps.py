from dependency_injector.wiring import Provide, inject
from fastapi import Depends

from src.app.api.fastapi.v1.services.chat import ChatService
from src.app.container import Container
from src.core.config import Settings
from src.core.rate_limit.message_limiter import MessageLimiter
from src.infrastructure.store.session import SessionStore


@inject
def get_settings_dep(
    settings: Settings = Depends(Provide[Container.settings]),  # noqa: B008
) -> Settings:
    """Application settings"""
    return settings


@inject
def get_chat_service(
    service: ChatService = Depends(Provide[Container.chat_service]),  # noqa: B008
) -> ChatService:
    """Chat service bound to the shared agent"""
    return service


@inject
def get_session_store(
    store: SessionStore = Depends(Provide[Container.session_store]),  # noqa: B008
) -> SessionStore:
    """In-memory store of every tab's chat session"""
    return store


@inject
def get_message_limiter(
    limiter: MessageLimiter = Depends(Provide[Container.message_limiter]),  # noqa: B008
) -> MessageLimiter:
    """Per-cookie and per-IP chat message limiter"""
    return limiter
