from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.core.config import R2Settings, StorageSettings
from src.core.exceptions import ServiceUnavailable


class Storage(Protocol):
    async def put(
        self, key: str, body: bytes, content_type: str, cache_control: str
    ) -> None:
        """Write a public file, replacing any at the key"""


class LocalStorage:
    def __init__(self, root: Path):
        """Write files under a directory, for development without R2"""
        self._root = root

    async def put(
        self, key: str, body: bytes, content_type: str, cache_control: str
    ) -> None:
        """Write the file under the root; headers have nowhere to go"""
        path = self._root / key
        try:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, body)
        except OSError as error:
            raise ServiceUnavailable(f"{key} could not be written") from error


class R2Storage:
    def __init__(self, settings: R2Settings):
        """Write to the public R2 bucket through its S3 API"""
        self._bucket = settings.bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.access_key_id.get_secret_value(),
            aws_secret_access_key=settings.secret_access_key.get_secret_value(),
            region_name="auto",
        )

    async def put(
        self, key: str, body: bytes, content_type: str, cache_control: str
    ) -> None:
        """Upload the file with its content type and cache header"""
        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
                CacheControl=cache_control,
            )
        except (BotoCoreError, ClientError) as error:
            raise ServiceUnavailable(f"{key} could not be written to R2") from error


def create_storage(settings: StorageSettings) -> Storage:
    """R2 once its settings are set, else the local directory"""
    return (
        R2Storage(settings.r2)
        if settings.r2.configured
        else LocalStorage(settings.local_dir)
    )


__all__ = ["LocalStorage", "R2Storage", "Storage", "create_storage"]
