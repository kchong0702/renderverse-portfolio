from dependency_injector import containers, providers


class Container(containers.DeclarativeContainer):
    executables = providers.List()
    """Graphs served as A2A agents; add a feature's Executable provider here"""
