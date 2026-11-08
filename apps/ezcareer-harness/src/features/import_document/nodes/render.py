from base64 import b64encode

import httpx

from src.clients.artifact_service import ArtifactServiceClient
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.state import ImportState


async def render(
    state: ImportState, artifact_service: ArtifactServiceClient
) -> ImportState:
    """Prints the draft through artifact-service"""
    try:
        rendered = await artifact_service.render(state["document"])
    except httpx.HTTPError as error:
        raise ImportFailed("couldn't print the draft; try again") from error
    return {"pdf": b64encode(rendered.artifact).decode(), "report": rendered.report}
