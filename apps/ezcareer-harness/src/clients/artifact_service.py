from base64 import b64decode, b64encode
from collections.abc import Mapping

import httpx
from document_schema import AnyDocument, DocumentKind, FileHash, Report, TemplateSpec
from pydantic import BaseModel, ConfigDict, TypeAdapter


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


class ArtifactServiceClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        """Lists templates, prints documents and converts files to PDF through
        artifact-service"""
        self._client = client
        """Client whose base_url ends in artifact-service's route prefix"""

    async def list_templates(self, kind: DocumentKind) -> list[TemplateSpec]:
        """The templates a document of kind can be printed with"""
        response = await self._client.get("/v1/templates", params={"kind": kind})
        response.raise_for_status()
        return TypeAdapter(list[TemplateSpec]).validate_json(response.content)

    async def render(
        self, document: AnyDocument, assets: Mapping[FileHash, bytes] = {}
    ) -> Rendered:
        """Prints a document in its design's template; assets holds the bytes of
        every file the document uses"""
        response = await self._client.post(
            "/v1/render",
            json={
                "document": document.model_dump(mode="json"),
                "assets": {
                    key: b64encode(data).decode() for key, data in assets.items()
                },
            },
        )
        response.raise_for_status()
        return Rendered.model_validate_json(response.content)

    async def convert(self, file: bytes) -> bytes:
        """The file as a PDF: a PDF as it is, a Word file converted"""
        response = await self._client.post(
            "/v1/convert", json={"file": b64encode(file).decode()}
        )
        response.raise_for_status()
        return b64decode(response.json()["pdf"])
