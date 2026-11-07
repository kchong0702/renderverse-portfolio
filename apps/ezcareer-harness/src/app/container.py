from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver

from src.app.a2a import Executable
from src.features import write_document


class Container(containers.DeclarativeContainer):
    executables = providers.List(
        providers.Singleton(
            Executable,
            name="edit-document",
            description="Propose a checked changeset for a chat request to change a résumé or cover letter",
            input_schema=write_document.EditInput,
            graph=providers.Singleton(
                write_document.edit_graph,
                render=providers.Singleton(write_document.artifact_service_render),
                checkpointer=providers.Singleton(InMemorySaver),
            ),
        ),
    )
    """Graphs served as A2A agents; add a feature's Executable provider here"""
