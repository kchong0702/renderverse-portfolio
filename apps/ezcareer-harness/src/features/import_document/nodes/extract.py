import httpx

from src.clients.artifact_service import ArtifactServiceClient
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.layout import suggest_look
from src.features.import_document.state import ImportState
from src.infrastructure import get_logger
from src.shared.extraction import UnreadableFile, extract_lines


async def extract(
    state: ImportState, artifact_service: ArtifactServiceClient
) -> ImportState:
    """Reads the upload's text lines and suggested look from the PDF artifact-service makes"""
    try:
        pdf = await artifact_service.convert(state["file"])
    except httpx.TransportError as error:
        raise ImportFailed("couldn't read the file; try again") from error
    except httpx.HTTPStatusError as error:
        get_logger(__name__).warning(
            "artifact-service convert failed",
            status=error.response.status_code,
            body=error.response.text,
        )
        if error.response.is_server_error:
            raise ImportFailed("couldn't read the file; try again") from error
        raise ImportFailed(error.response.json()["detail"]) from error
    try:
        return {"lines": extract_lines(pdf), "suggestion": suggest_look(pdf)}
    except UnreadableFile as error:
        raise ImportFailed(str(error)) from error
