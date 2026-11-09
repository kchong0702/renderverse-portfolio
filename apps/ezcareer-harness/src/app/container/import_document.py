from dependency_injector import containers, providers

from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.features import import_document


class ImportDocumentContainer(containers.DeclarativeContainer):
    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    artifact_service = providers.Dependency(instance_of=ArtifactServiceClient)
    """Prints the imported draft"""

    import_resume_executable = providers.Singleton(
        Executable,
        name="import-resume",
        description="Turn an uploaded résumé (PDF or Word, base64 in file) into a draft document whose values cite the file's lines, printed to PDF",
        graph=providers.Singleton(
            import_document.build_graph,
            artifact_service=artifact_service,
            checkpointer=checkpointer,
        ),
    )
    """The import-resume workflow served over A2A"""
