from uuid import uuid4

from document_schema import (
    AnyDocument,
    AnyEdit,
    Changeset,
    Delete,
    InsertItem,
    apply_edits,
)
from langgraph.runtime import Runtime

from src.features.write_document.state import EditContext, EditGraphState

_TRIMS = 5
"""Bullets page-fit may remove before it hands the changeset over as it is"""


def _touched(edit: AnyEdit) -> str:
    """The path an edit writes to, so page-fit never removes it"""
    if isinstance(edit, InsertItem):
        return f"{edit.parent}/{edit.item.get('id')}"
    return getattr(edit, "path", "")


def _trim(document: AnyDocument, edits: list[AnyEdit]) -> Delete | None:
    """Deletes a bullet from the entry with the most, the later entry on a tie,
    keeping one bullet per entry and every bullet the edits wrote"""
    touched = [_touched(edit) for edit in edits]
    bullet_counts: dict[str, int] = {}
    for block in reversed(document.content.blocks):
        for entry in reversed(getattr(block, "items", [])):
            bullets = getattr(entry, "bullets", [])
            paths = [
                f"blocks/{block.id}/items/{entry.id}/bullets/{bullet.id}"
                for bullet in bullets
            ]
            free = [
                path
                for path in paths
                if not any(t == path or t.startswith(f"{path}/") for t in touched)
            ]
            if not block.hidden and len(bullets) > 1 and free:
                bullet_counts[free[-1]] = len(bullets)
    if not bullet_counts:
        return None
    return Delete(kind="delete", path=max(bullet_counts, key=bullet_counts.__getitem__))


async def page_fit(state: EditGraphState, runtime: Runtime[EditContext]) -> dict:
    """Removes bullets in code until the edited document prints on no more
    pages than before, and adds those deletes to the changeset"""
    render = runtime.context.render
    pages = (state["report"] or await render(state["document"])).pages
    changeset: Changeset = state["structured_response"]
    edits = list(changeset.edits)
    for _ in range(_TRIMS):
        edited = apply_edits(state["document"], edits)
        if (await render(edited)).pages <= pages or not (trim := _trim(edited, edits)):
            break
        edits.append(trim)
    return {
        "changeset": changeset.model_copy(
            update={"id": uuid4().hex, "agent": "career-consultant", "edits": edits}
        )
    }
