from collections.abc import Callable, Mapping


class Factory[T]:
    def __init__(self, builders: Mapping[str, Callable[[], T]]) -> None:
        """Builds the items it knows by name, each once"""
        self._builders = builders
        self._created: dict[str, T] = {}

    def create(self, name: str) -> T:
        """The item called name: built the first time it's asked for, the same one after"""
        if name not in self._builders:
            raise ValueError(f"Unknown {name!r}; known: {sorted(self._builders)}")
        if name not in self._created:
            self._created[name] = self._builders[name]()
        return self._created[name]
