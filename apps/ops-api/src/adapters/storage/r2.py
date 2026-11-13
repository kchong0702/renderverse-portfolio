from __future__ import annotations

import asyncio
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from src.adapters.storage.schemas import UploadTarget
from src.core.config import R2Settings
from src.core.exceptions import ServiceUnavailable


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


__all__ = ["R2Storage"]
