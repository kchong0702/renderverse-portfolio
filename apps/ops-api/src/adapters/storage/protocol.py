from __future__ import annotations

from typing import Protocol

from src.adapters.storage.schemas import UploadTarget


class Storage(Protocol):
    async def put(
        self, key: str, body: bytes, content_type: str, cache_control: str
    ) -> None:
        """Write a public file, replacing any at the key"""

    def upload_target(
        self, key: str, content_type: str, size: int, checksum: str
    ) -> UploadTarget:
        """Where the browser uploads a private file whose base64 SHA-256 is checksum"""

    def download_url(self, key: str) -> str:
        """A short-lived URL the browser reads a private file from"""

    async def put_private(self, key: str, body: bytes, content_type: str) -> None:
        """Write a private file, replacing any at the key"""

    async def read_private(self, key: str) -> bytes:
        """A private file's bytes"""

    async def size(self, key: str) -> int | None:
        """A private file's size, or None when it is missing"""

    async def delete(self, key: str) -> None:
        """Delete a private file, if it exists"""

    async def publish(self, key: str, public_key: str) -> None:
        """Copy a private file to the public key"""

    async def public_keys(self, prefix: str) -> list[str]:
        """The public keys under the prefix"""

    async def unpublish(self, public_key: str) -> None:
        """Delete a public file, if it exists"""


__all__ = ["Storage"]
