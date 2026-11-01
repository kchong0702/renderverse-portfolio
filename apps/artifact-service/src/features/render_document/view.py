from collections.abc import Collection
from typing import Any

from document_schema import Content, SectionKind

from src.features.render_document.schemas import ContentView, View


def _add_paths(node: Any, path: str, paths: list[str]) -> None:
    if isinstance(node, list):
        for entry in node:
            _add_paths(entry, f"{path}/{entry['id']}", paths)
    elif isinstance(node, dict):
        if node.keys() == {"text", "src"}:
            node["path"] = path
            paths.append(path)
            return
        for key, value in node.items():
            _add_paths(value, f"{path}/{key}" if path else key, paths)


def build_view(content: Content, hidden: Collection[str]) -> View:
    data = content.model_dump(mode="json")
    data["sections"] = [s for s in data["sections"] if s["id"] not in hidden]
    for section in data["sections"]:
        section.update({f"is_{kind}": section["kind"] == kind for kind in SectionKind})
    paths: list[str] = []
    _add_paths(data, "", paths)
    return View(content=ContentView.model_validate(data), value_paths=paths)
