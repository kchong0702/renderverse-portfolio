import httpx
from dependency_injector import containers, providers

from src.app.a2a import Executable
from src.core.config import get_settings
from src.features import import_document
from src.shared.clients.artifact_service import ArtifactService

_settings = get_settings()


class Container(containers.DeclarativeContainer):
    executables = providers.List(
        providers.Singleton(
            Executable,
            name="import-resume",
            description="Turn an uploaded résumé (PDF or Word, base64 in file) into a "
            "draft document whose values cite the file's lines, printed to PDF",
            input_schema=import_document.ImportInput,
            graph=providers.Singleton(
                import_document.build_task_graph,
                config=providers.Singleton(import_document.ImportConfig.load),
                artifacts=providers.Singleton(
                    ArtifactService,
                    client=providers.Singleton(
                        httpx.AsyncClient,
                        base_url=_settings.artifact_service.url,
                        timeout=_settings.artifact_service.timeout_s,
                    ),
                ),
            ),
        ),
    )
    """Graphs served as A2A agents; add a feature's Executable provider here"""
