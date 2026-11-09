from collections.abc import Iterator

from document_schema import RichValue, Value
from pydantic import BaseModel


def cited_values(node: object, path: str) -> Iterator[tuple[str, Value | RichValue]]:
    """Every Value and RichValue under node, with its path of ids or indexes"""
    if isinstance(node, Value | RichValue):
        yield path, node
    elif isinstance(node, BaseModel):
        for name in type(node).model_fields:
            yield from cited_values(getattr(node, name), f"{path}/{name}")
    elif isinstance(node, list):
        for index, item in enumerate(node):
            yield from cited_values(item, f"{path}/{getattr(item, 'id', index)}")
