import json
from base64 import b64decode, b64encode

import httpx
import pytest

from src.clients.artifact_service import ArtifactServiceClient


def _convert(request: httpx.Request) -> httpx.Response:
    """Converts a file by prefixing %PDF, and refuses an empty one"""
    file = b64decode(json.loads(request.content)["file"])
    if not file:
        return httpx.Response(
            422, json={"detail": "upload a PDF or a Word (.docx) file"}
        )
    return httpx.Response(200, json={"pdf": b64encode(b"%PDF " + file).decode()})


def _client() -> ArtifactServiceClient:
    """An ArtifactServiceClient on a fake artifact-service that converts files"""
    return ArtifactServiceClient(
        httpx.AsyncClient(
            transport=httpx.MockTransport(_convert),
            base_url="http://artifact-service",
        )
    )


async def test_convert_returns_the_file_as_a_pdf():
    assert await _client().convert(b"word") == b"%PDF word"


async def test_a_file_artifact_service_refuses_raises():
    with pytest.raises(httpx.HTTPStatusError) as raised:
        await _client().convert(b"")

    assert raised.value.response.status_code == 422
