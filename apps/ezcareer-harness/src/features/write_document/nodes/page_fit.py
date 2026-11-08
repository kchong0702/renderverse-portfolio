from uuid import uuid4

import httpx
from document_schema import (
    AnyDocument,
    AnyEdit,
    Awards,
    Certifications,
    Custom,
    Delete,
    Education,
    Experience,
    InsertBlock,
    InsertItem,
    Move,
    Projects,
    Publications,
    UpdateField,
    apply_edits,
)

from src.clients.artifact_service import ArtifactServiceClient
from src.core.errors import ExecuteError
from src.features.write_document.state import EditGraphState


def _trim(document: AnyDocument, edits: list[AnyEdit]) -> Delete | None:
    """A delete of one bullet from the entry with the most, the later on a tie, sparing
    each entry's last bullet and every bullet the edits wrote; None when none can go"""
    touched = (
        [edit.path for edit in edits if isinstance(edit, UpdateField | Move | Delete)]
        + [
            f"{edit.parent}/{edit.item.get('id')}"
            for edit in edits
            if isinstance(edit, InsertItem)
        ]
        + [f"blocks/{edit.block.id}" for edit in edits if isinstance(edit, InsertBlock)]
    )
    bullet_counts: dict[str, int] = {}
    for block in reversed(document.content.blocks):
        if block.hidden or not isinstance(
            block,
            Experience
            | Projects
            | Education
            | Awards
            | Certifications
            | Publications
            | Custom,
        ):
            continue
        for entry in reversed(block.items):
            free = [
                path
                for path in (
                    f"blocks/{block.id}/items/{entry.id}/bullets/{bullet.id}"
                    for bullet in entry.bullets
                )
                if not any(
                    t == path or t.startswith(f"{path}/") or path.startswith(f"{t}/")
                    for t in touched
                )
            ]
            if len(entry.bullets) > 1 and free:
                bullet_counts[free[-1]] = len(entry.bullets)
    if not bullet_counts:
        return None
    return Delete(kind="delete", path=max(bullet_counts, key=bullet_counts.__getitem__))


async def page_fit(
    state: EditGraphState, artifact_service: ArtifactServiceClient, trims: int
) -> EditGraphState:
    """Deletes bullets until the edited document prints on no more pages than
    before, and adds those deletes to the changeset"""
    document, assets = state["document"], state.get("assets", {})
    changeset = state["structured_response"]
    edits = list(changeset.edits)
    try:
        pages = (
            state.get("report")
            or (await artifact_service.render(document, assets)).report
        ).pages
        for _ in range(trims):
            edited = apply_edits(document, edits)
            if (
                await artifact_service.render(edited, assets)
            ).report.pages <= pages or not (trim := _trim(edited, edits)):
                break
            edits.append(trim)
    except httpx.HTTPError as error:
        raise ExecuteError(f"Couldn't print the edited document: {error}") from error
    return {
        "changeset": changeset.model_copy(
            update={"id": uuid4().hex, "agent": "career-consultant", "edits": edits}
        )
    }
