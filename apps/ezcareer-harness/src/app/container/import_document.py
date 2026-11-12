from dependency_injector import containers, providers

from src.agents import build_agent
from src.app.a2a import Executable
from src.clients.artifact_service import ArtifactServiceClient
from src.features import import_document, import_profile


class ImportDocumentContainer(containers.DeclarativeContainer):
    registry = providers.Dependency(instance_of=dict)
    """Every registered agent, by name"""

    checkpointer = providers.Dependency()
    """Where the served graph keeps checkpoints"""

    artifact_service = providers.Dependency(instance_of=ArtifactServiceClient)
    """Prints the imported draft"""

    agent = providers.Singleton(
        build_agent,
        agent=registry.provided["document-analyst"],
        response_formats=(import_document.ResumeImport, import_profile.ProfileImport),
    )
    """The document-analyst agent, built once"""

    import_resume_executable = providers.Singleton(
        Executable,
        name="import-resume",
        description="Turn an uploaded résumé (PDF or Word, base64 in file) into a draft document whose values cite the file's lines, printed to PDF",
        graph=providers.Singleton(
            import_document.build_graph,
            agent=agent,
            artifact_service=artifact_service,
            checkpointer=checkpointer,
        ),
    )
    """The import-resume workflow served over A2A"""

    import_profile_executable = providers.Singleton(
        Executable,
        name="import-profile",
        description="Turn the unpacked files of a profile export, such as a LinkedIn data export, into profile facts whose values come word for word from the export",
        graph=providers.Singleton(
            import_profile.build_graph, agent=agent, checkpointer=checkpointer
        ),
    )
    """The import-profile workflow served over A2A"""
