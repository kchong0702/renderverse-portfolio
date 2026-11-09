from __future__ import annotations

import httpx2
from pydantic import ValidationError

from src.core.config import EzcareerSettings
from src.core.exceptions import ServiceUnavailable
from src.integrations.ezcareer.schemas import ModelCatalog


class EzcareerClient:
    def __init__(
        self,
        settings: EzcareerSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime; tests pass a mock transport"""
        self._http = httpx2.AsyncClient(
            base_url=settings.url,
            timeout=settings.timeout_seconds,
            transport=transport,
        )

    async def models(self) -> ModelCatalog:
        """The models ezcareer-harness offers, by provider"""
        try:
            response = await self._http.get("models")
            response.raise_for_status()
            return ModelCatalog.model_validate_json(response.content)
        except (httpx2.HTTPError, ValidationError) as error:
            raise ServiceUnavailable(
                "ezcareer-harness did not return its models; try again later"
            ) from error

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["EzcareerClient"]
