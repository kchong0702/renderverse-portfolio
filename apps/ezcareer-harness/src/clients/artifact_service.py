import httpx
from document_schema import DocumentKind, TemplateSpec
from pydantic import TypeAdapter


class ArtifactServiceClient:
    def __init__(self, client: httpx.AsyncClient) -> None:
        """Lists templates and prints documents through artifact-service"""
        self._client = client
        """Client whose base_url ends in artifact-service's route prefix"""

    async def list_templates(self, kind: DocumentKind) -> list[TemplateSpec]:
        """The templates a document of kind can be printed with"""
        response = await self._client.get("/v1/templates", params={"kind": kind})
        response.raise_for_status()
        return TypeAdapter(list[TemplateSpec]).validate_json(response.content)
