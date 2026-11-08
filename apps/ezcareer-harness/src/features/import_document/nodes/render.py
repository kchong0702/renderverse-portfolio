from base64 import b64encode

import httpx

from src.clients.artifact_service import ArtifactServiceClient
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.state import ImportState
from src.infrastructure import get_logger


async def render(
    state: ImportState, artifact_service: ArtifactServiceClient
) -> ImportState:
    """Prints the draft through artifact-service"""
    try:
        rendered = await artifact_service.render(state["document"])
    except httpx.TransportError as error:
        raise ImportFailed("couldn't print the draft; try again") from error
    except httpx.HTTPStatusError as error:
        get_logger(__name__).warning(
            "artifact-service render failed",
            status=error.response.status_code,
            body=error.response.text,
        )
        if error.response.is_server_error:
            raise ImportFailed("couldn't print the draft; try again") from error
        raise ImportFailed("the draft couldn't be printed") from error
    return {"pdf": b64encode(rendered.artifact).decode(), "report": rendered.report}
