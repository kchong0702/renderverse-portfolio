from __future__ import annotations

from typing import Protocol

from pydantic import SecretStr

from src.adapters.job_sources.schemas import JobQuery, JobSearchResults
from src.core.providers import Provider


class JobSource(Protocol):
    provider: Provider
    """The connection that holds each user's key to the source"""

    label: str
    """The source's name as Settings shows it, such as JSearch"""

    encryption_key: SecretStr
    """The Fernet key the users' stored keys to the source are encrypted with"""

    async def search(self, query: JobQuery, api_key: str) -> JobSearchResults:
        """The postings the query finds on the user's key, with the key's quota;
        InvalidInput when the source refuses the key, ServiceUnavailable when it fails"""
        ...

    async def aclose(self) -> None:
        """Close the source's connections"""
        ...


__all__ = ["JobSource"]
