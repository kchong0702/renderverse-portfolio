from dependency_injector import containers, providers

from src.app.a2a import Executable
from src.features import import_document


class Container(containers.DeclarativeContainer):
    executables = providers.List(
        providers.Singleton(
            Executable,
            name="import-resume",
            description="Turn an uploaded résumé (PDF or Word, base64 in file) into a "
            "draft document whose values cite the file's lines, printed to PDF",
            input_schema=import_document.ImportInput,
            graph=providers.Singleton(import_document.build_task_graph),
        ),
    )
    """Graphs served as A2A agents; add a feature's Executable provider here"""
