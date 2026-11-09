from collections.abc import Iterable
from typing import Any

from pydantic import TypeAdapter

from document_schema.document import AnyDocument
from document_schema.edits import (
    AnyEdit,
    Delete,
    InsertBlock,
    InsertItem,
    Move,
    UpdateDesign,
    UpdateField,
    UpdateVisibility,
)
from document_schema.types import DataFieldPath, Id

_DOCUMENT: TypeAdapter[AnyDocument] = TypeAdapter(AnyDocument)


def _child(node: Any, key: str, path: DataFieldPath) -> Any:
    """The field named key, or the list item whose id is key"""
    if isinstance(node, list):
        if found := [item for item in node if item.get("id") == key]:
            return found[0]
    elif isinstance(node, dict) and key in node:
        return node[key]
    raise ValueError(f"{path}: {key} not found")


def _walk(content: dict[str, Any], path: DataFieldPath) -> Any:
    """The field or item a path names, starting at the content"""
    node: Any = content
    for key in path.split("/"):
        node = _child(node, key, path)
    return node


def _items(content: dict[str, Any], path: DataFieldPath) -> list[Any]:
    """The list a path names"""
    match _walk(content, path):
        case list() as items:
            return items
        case _:
            raise ValueError(f"{path}: not a list")


def _position(items: list[Any], after: Id | None, path: DataFieldPath) -> int:
    """Index just past the item named by after; 0 when after is None"""
    return 0 if after is None else items.index(_child(items, after, path)) + 1


def _apply(data: dict[str, Any], edit: AnyEdit) -> None:
    """Makes one edit in place on a document's JSON"""
    content = data["content"]
    match edit:
        case UpdateField(path=path):
            parent, key = path.rpartition("/")[::2]
            match _walk(content, parent) if parent else content:
                case dict() as node if key in node:
                    node[key] = edit.model_dump(mode="json")["value"]
                case _:
                    raise ValueError(f"{path}: not a field")
        case InsertBlock(after=after):
            blocks = content["blocks"]
            blocks.insert(
                _position(blocks, after, "blocks"),
                edit.model_dump(mode="json")["block"],
            )
        case InsertItem(parent=parent, after=after):
            items = _items(content, parent)
            items.insert(
                _position(items, after, parent), edit.model_dump(mode="json")["item"]
            )
        case Move(path=path, after=after):
            items = _items(content, path.rpartition("/")[0])
            items.remove(moved := _walk(content, path))
            items.insert(_position(items, after, path), moved)
        case Delete(path=path):
            parent, key = path.rpartition("/")[::2]
            match _walk(content, parent) if parent else content:
                case list() as items:
                    items.remove(_child(items, key, path))
                case dict() as node if key in node:
                    del node[key]
                case _:
                    raise ValueError(f"{path}: {key} not found")
        case UpdateVisibility(block=block, hidden=hidden):
            _child(content["blocks"], block, f"blocks/{block}")["hidden"] = hidden
        case UpdateDesign():
            data["design"] = edit.model_dump(mode="json")["design"]


def apply_edits(document: AnyDocument, edits: Iterable[AnyEdit]) -> AnyDocument:
    """Returns the document with the edits made in order
    Raises ValueError for a path that isn't there or a result that isn't valid"""
    data = document.model_dump(mode="json")
    for edit in edits:
        _apply(data, edit)
    return _DOCUMENT.validate_python(data)
