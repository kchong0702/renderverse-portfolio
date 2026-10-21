from dependency_injector import containers, providers

from src.core.graph import build_chat_graph
from src.shared.model_factory import create_model


class Container(containers.DeclarativeContainer):
    chat_model = providers.Singleton(create_model)

    chat_graph = providers.Singleton(build_chat_graph, model=chat_model)
