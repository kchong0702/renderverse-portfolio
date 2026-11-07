from base64 import b64encode
from typing import Any

import httpx
from document_schema import AnyDocument, FileHash, Report
from pydantic import BaseModel, ConfigDict


class Rendered(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        val_json_bytes="base64",
    )

    artifact: bytes
    """The printed PDF"""

    report: Report
    """How the pages came out"""


class ArtifactService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        """Client whose base_url ends in artifact-service's route prefix"""

    async def render(
        self,
        document: AnyDocument,
        template: dict[str, Any],
        assets: dict[FileHash, bytes],
    ) -> Rendered:
        """Prints a document with a template spec; assets holds the bytes of every
        file the document uses"""
        response = await self._client.post(
            "/v1/render",
            json={
                "document": document.model_dump(mode="json"),
                "template": template,
                "assets": {
                    key: b64encode(data).decode() for key, data in assets.items()
                },
            },
        )
        response.raise_for_status()
        return Rendered.model_validate_json(response.content)
