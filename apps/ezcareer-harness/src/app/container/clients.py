import httpx
from dependency_injector import containers, providers

from src.adapters.job_sources import SearchProtocol
from src.adapters.job_sources.jsearch import JSearchAdapter
from src.clients.artifact_service import ArtifactServiceClient
from src.core.config import Settings
from src.shared.factory import Factory


class ClientsContainer(containers.DeclarativeContainer):
    settings = providers.Dependency(instance_of=Settings)
    """The app's settings"""

    job_sources = providers.Singleton(
        Factory[SearchProtocol], {"jsearch": JSearchAdapter}
    )
    """Job sources by name, each created once"""

    artifact_service = providers.Singleton(
        ArtifactServiceClient,
        client=providers.Singleton(
            httpx.AsyncClient,
            base_url=settings.provided.artifact_service.url.encoded_string.call(),
            timeout=settings.provided.artifact_service.timeout_seconds,
            transport=providers.Singleton(
                httpx.AsyncHTTPTransport,
                retries=settings.provided.artifact_service.retries,
            ),
        ),
    )
    """artifact-service's client, on its URL, render timeout and connection retries"""
