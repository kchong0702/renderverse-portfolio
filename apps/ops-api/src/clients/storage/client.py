from __future__ import annotations

import asyncio
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import IO, Any, Protocol

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.clients.storage.schemas import UploadTarget
from src.core.config import R2Settings, StorageSettings
from src.core.exceptions import ServiceUnavailable


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


class LocalStorage:
    def __init__(self, root: Path, private_root: Path, url: str):
        """Keep public and private files in two directories, for development"""
        self._root = root
        self._private_root = private_root
        self._url = url

    async def put(
        self, key: str, body: bytes, content_type: str, cache_control: str
    ) -> None:
        """Write the file under the root; headers have nowhere to go"""
        await self._write(self._root / key, body)

    def upload_target(
        self, key: str, content_type: str, size: int, checksum: str
    ) -> UploadTarget:
        """The ops-api route that writes the private file"""
        return UploadTarget(
            url=f"{self._url}/{PurePosixPath(key).name}",
            headers={"Content-Type": content_type},
        )

    def download_url(self, key: str) -> str:
        """The ops-api route that reads the private file"""
        return f"{self._url}/{PurePosixPath(key).name}"

    async def put_private(self, key: str, body: bytes, content_type: str) -> None:
        """Write the file under the private root"""
        await self._write(self._private_root / key, body)

    async def read_private(self, key: str) -> bytes:
        """The private file's bytes"""
        try:
            return await asyncio.to_thread((self._private_root / key).read_bytes)
        except OSError as error:
            raise ServiceUnavailable(f"{key} could not be read") from error

    async def size(self, key: str) -> int | None:
        """The private file's size, or None when it is missing"""
        path = self._private_root / key
        return path.stat().st_size if path.is_file() else None

    async def delete(self, key: str) -> None:
        """Delete the private file, if it exists"""
        (self._private_root / key).unlink(missing_ok=True)

    async def publish(self, key: str, public_key: str) -> None:
        """Copy the private file under the root"""
        target = self._root / public_key
        try:
            await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(shutil.copyfile, self._private_root / key, target)
        except OSError as error:
            raise ServiceUnavailable(f"{key} could not be published") from error

    async def public_keys(self, prefix: str) -> list[str]:
        """The files under the root whose keys start with the prefix"""
        return sorted(
            key
            for path in self._root.rglob("*")
            if path.is_file()
            and (key := path.relative_to(self._root).as_posix()).startswith(prefix)
        )

    async def unpublish(self, public_key: str) -> None:
        """Delete the file under the root, if it exists"""
        (self._root / public_key).unlink(missing_ok=True)

    @contextmanager
    def write_private(self, key: str) -> Iterator[IO[bytes]]:
        """A temp file that becomes the private file only if the block succeeds"""
        path = self._private_root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=path.parent, delete_on_close=False) as file:
            yield file
            file.close()
            Path(file.name).replace(path)

    def private_path(self, key: str) -> Path | None:
        """Where a private file is kept, or None when it is missing"""
        path = self._private_root / key
        return path if path.is_file() else None

    async def _write(self, path: Path, body: bytes) -> None:
        """Write the file, making its directory"""
        try:
            await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
            await asyncio.to_thread(path.write_bytes, body)
        except OSError as error:
            raise ServiceUnavailable(f"{path.name} could not be written") from error


class R2Storage:
    def __init__(self, settings: R2Settings):
        """Use the public and private R2 buckets through their S3 API"""
        self._bucket = settings.bucket
        self._private_bucket = settings.private_bucket
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
        await self._call(
            "put_object",
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            CacheControl=cache_control,
        )

    def upload_target(
        self, key: str, content_type: str, size: int, checksum: str
    ) -> UploadTarget:
        """A presigned PUT bound to the file's type, size and SHA-256"""
        return UploadTarget(
            url=self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._private_bucket,
                    "Key": key,
                    "ContentType": content_type,
                    "ContentLength": size,
                    "ChecksumSHA256": checksum,
                },
                ExpiresIn=15 * 60,
            ),
            headers={"Content-Type": content_type, "x-amz-checksum-sha256": checksum},
        )

    def download_url(self, key: str) -> str:
        """A presigned GET from the private bucket, valid for an hour"""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._private_bucket, "Key": key},
            ExpiresIn=60 * 60,
        )

    async def put_private(self, key: str, body: bytes, content_type: str) -> None:
        """Upload the file to the private bucket with its content type"""
        await self._call(
            "put_object",
            Bucket=self._private_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
        )

    async def read_private(self, key: str) -> bytes:
        """The private object's bytes"""
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._private_bucket, Key=key
            )
            return await asyncio.to_thread(response["Body"].read)
        except (BotoCoreError, ClientError) as error:
            raise ServiceUnavailable(f"{key} could not be read from R2") from error

    async def size(self, key: str) -> int | None:
        """The private object's size, or None when it is missing"""
        try:
            head = await asyncio.to_thread(
                self._client.head_object, Bucket=self._private_bucket, Key=key
            )
        except ClientError as error:
            if error.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
                return None
            raise ServiceUnavailable(f"{key} could not be read from R2") from error
        except BotoCoreError as error:
            raise ServiceUnavailable(f"{key} could not be read from R2") from error
        return int(head["ContentLength"])

    async def delete(self, key: str) -> None:
        """Delete the private object"""
        await self._call("delete_object", Bucket=self._private_bucket, Key=key)

    async def publish(self, key: str, public_key: str) -> None:
        """Copy the private object into the public bucket, with its content type"""
        await self._call(
            "copy_object",
            Bucket=self._bucket,
            Key=public_key,
            CopySource={"Bucket": self._private_bucket, "Key": key},
        )

    async def public_keys(self, prefix: str) -> list[str]:
        """Every public key under the prefix, across pages"""

        def list_keys() -> list[str]:
            pages = self._client.get_paginator("list_objects_v2").paginate(
                Bucket=self._bucket, Prefix=prefix
            )
            return sorted(
                item["Key"] for page in pages for item in page.get("Contents", [])
            )

        try:
            return await asyncio.to_thread(list_keys)
        except (BotoCoreError, ClientError) as error:
            raise ServiceUnavailable(f"{prefix} could not be listed in R2") from error

    async def unpublish(self, public_key: str) -> None:
        """Delete the public object"""
        await self._call("delete_object", Bucket=self._bucket, Key=public_key)

    async def _call(self, operation: str, **params: Any) -> None:
        """Run an S3 operation off the event loop; an R2 error is a service error"""
        try:
            await asyncio.to_thread(getattr(self._client, operation), **params)
        except (BotoCoreError, ClientError) as error:
            raise ServiceUnavailable(
                f"{params['Key']} could not be written to R2"
            ) from error


def create_storage(settings: StorageSettings, route_prefix: str) -> Storage:
    """R2 once its settings are set, else local directories served by ops-api"""
    return (
        R2Storage(settings.r2)
        if settings.r2.configured
        else LocalStorage(
            settings.local_dir,
            settings.local_private_dir,
            f"{route_prefix}/v1/portfolio/uploads",
        )
    )


__all__ = ["LocalStorage", "R2Storage", "Storage", "create_storage"]
