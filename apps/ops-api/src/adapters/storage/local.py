from __future__ import annotations

import asyncio
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import IO

from src.adapters.storage.schemas import UploadTarget
from src.core.exceptions import ServiceUnavailable


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


__all__ = ["LocalStorage"]
