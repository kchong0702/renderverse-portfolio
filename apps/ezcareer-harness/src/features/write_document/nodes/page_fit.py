from uuid import uuid4

import httpx
from document_schema import (
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


async def page_fit(
    state: EditGraphState, artifact_service: ArtifactServiceClient, trims: int
) -> EditGraphState:
    """Adds bullet deletes to the changeset until it prints on no more pages than before,
    from the entry with the most, never an entry's last bullet or one the edits wrote"""
    document, assets = state["document"], state.get("assets", {})
    changeset = state["structured_response"]
    edits = list(changeset.edits)
    touched = (
        [edit.path for edit in edits if isinstance(edit, UpdateField | Move | Delete)]
        + [
            f"{edit.parent}/{edit.item.get('id')}"
            for edit in edits
            if isinstance(edit, InsertItem)
        ]
        + [f"blocks/{edit.block.id}" for edit in edits if isinstance(edit, InsertBlock)]
    )
    try:
        pages = (
            state.get("report")
            or (await artifact_service.render(document, assets)).report
        ).pages
        for _ in range(trims):
            edited = apply_edits(document, edits)
            if (await artifact_service.render(edited, assets)).report.pages <= pages:
                break
            free = [
                (path, len(entry.bullets))
                for block in reversed(edited.content.blocks)
                if not block.hidden
                and isinstance(
                    block,
                    Experience
                    | Projects
                    | Education
                    | Awards
                    | Certifications
                    | Publications
                    | Custom,
                )
                for entry in reversed(block.items)
                if len(entry.bullets) > 1
                for bullet in reversed(entry.bullets)
                for path in [f"blocks/{block.id}/items/{entry.id}/bullets/{bullet.id}"]
                if not any(
                    t == path or t.startswith(f"{path}/") or path.startswith(f"{t}/")
                    for t in touched
                )
            ]
            if not free:
                break
            edits.append(
                Delete(kind="delete", path=max(free, key=lambda bullet: bullet[1])[0])
            )
    except httpx.HTTPError as error:
        raise ExecuteError(f"Couldn't print the edited document: {error}") from error
    return {
        "changeset": changeset.model_copy(
            update={"id": uuid4().hex, "agent": "career-consultant", "edits": edits}
        )
    }
