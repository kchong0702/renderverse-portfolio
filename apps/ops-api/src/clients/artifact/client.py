from __future__ import annotations

import httpx2
from document_schema import AnyDocument, DocumentKind, TemplateSpec

from src.clients.artifact.schemas import Render
from src.core.config import ArtifactSettings
from src.core.exceptions import ServiceUnavailable


class ArtifactClient:
    def __init__(
        self,
        settings: ArtifactSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime; tests pass a mock transport"""
        self._http = httpx2.AsyncClient(
            base_url=settings.url,
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    async def templates(self, kind: DocumentKind) -> list[TemplateSpec]:
        """The templates artifact-service can print a document of this kind with"""
        try:
            response = await self._http.get("v1/templates", params={"kind": kind})
            response.raise_for_status()
            return [TemplateSpec.model_validate(spec) for spec in response.json()]
        except (httpx2.HTTPError, ValueError) as error:
            raise ServiceUnavailable(
                "artifact-service did not return its templates; try again later"
            ) from error

    async def render(self, document: AnyDocument) -> Render:
        """The document printed as a PDF in its design's template
        Documents with assets fail until ops-api stores asset bytes"""
        try:
            response = await self._http.post(
                "v1/render",
                json={"document": document.model_dump(mode="json")},
            )
            response.raise_for_status()
            return Render.model_validate_json(response.content)
        except (httpx2.HTTPError, ValueError) as error:
            raise ServiceUnavailable(
                "artifact-service did not print the document; try again later"
            ) from error

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["ArtifactClient"]
