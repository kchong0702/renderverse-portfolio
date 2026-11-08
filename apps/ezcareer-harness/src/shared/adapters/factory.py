from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, create_model
from pydantic.fields import FieldInfo


class AdapterUnavailable(Exception):
    """An adapter can't run right now; the message says why and for how long"""


class Adapter[T](BaseModel):
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    name: str
    """The name config enables it by, such as jsearch"""

    query: type[BaseModel]
    """Its own arguments; a field named like another adapter's must have the
    same type, since they share it"""

    usage: str
    """What a run costs, for the description of the tool that runs it"""

    run: Callable[[Any], Awaitable[T]]
    """Runs it with a query of its own type"""


class Enabled[T](BaseModel):
    model_config = ConfigDict(
        frozen=True, arbitrary_types_allowed=True, use_attribute_docstrings=True
    )

    adapters: tuple[Adapter[T], ...]
    """The adapters config enables, in order"""

    @property
    def usage(self) -> str:
        """What a run costs on each enabled adapter"""
        return " ".join(adapter.usage for adapter in self.adapters)

    def arguments(self, name: str, **extra: Any) -> type[BaseModel]:
        """One argument model with every enabled adapter's fields, a single field per
        name, plus extra fields such as an injected runtime"""
        fields: dict[str, FieldInfo] = {}
        for adapter in self.adapters:
            for field_name, field in adapter.query.model_fields.items():
                if (
                    field_name in fields
                    and fields[field_name].annotation != field.annotation
                ):
                    raise ValueError(f"Adapters disagree on the type of {field_name!r}")
                fields.setdefault(field_name, field)
        return create_model(
            name,
            __config__=ConfigDict(extra="forbid", arbitrary_types_allowed=True),
            **extra,
            **{key: (field.annotation, field) for key, field in fields.items()},
        )

    async def run(self, given: Mapping[str, Any]) -> tuple[list[T], list[str]]:
        """Runs each enabled adapter on its own fields of given; returns the results
        of those that ran and why the others were unavailable"""
        results: list[T] = []
        unavailable: list[str] = []
        for adapter in self.adapters:
            query = adapter.query.model_validate(
                {
                    key: value
                    for key, value in given.items()
                    if key in adapter.query.model_fields
                }
            )
            try:
                results.append(await adapter.run(query))
            except AdapterUnavailable as error:
                unavailable.append(str(error))
        return results, unavailable


class AdapterFactory[T]:
    def __init__(self, *adapters: Adapter[T]) -> None:
        """Every adapter of one kind, by name"""
        self.adapters = {adapter.name: adapter for adapter in adapters}

    def enable(self, names: Sequence[str]) -> Enabled[T]:
        """The adapters config names, in its order; an unknown name fails"""
        unknown = set(names) - self.adapters.keys()
        if unknown:
            raise ValueError(
                f"Unknown adapters {sorted(unknown)}; known: {sorted(self.adapters)}"
            )
        return Enabled[T](adapters=tuple(self.adapters[name] for name in names))
