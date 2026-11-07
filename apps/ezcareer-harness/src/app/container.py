from a2a.server.tasks import InMemoryTaskStore
from dependency_injector import containers, providers
from langgraph.checkpoint.memory import InMemorySaver


class Container(containers.DeclarativeContainer):
    task_store = providers.Singleton(InMemoryTaskStore)
    """Where the A2A server keeps every task; swap in a database store here"""

    checkpointer = providers.Singleton(InMemorySaver)
    """Where graphs keep checkpoints so interrupted runs resume; pass it to
    each executable's graph, and swap in a database saver here"""

    executables = providers.List()
    """Graphs served as A2A agents; add a feature's Executable provider here"""
