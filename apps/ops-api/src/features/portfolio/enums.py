from __future__ import annotations

from enum import StrEnum
from typing import Literal

MediaSlot = Literal["image", "video"]
"""Which of a project's media a file is: its cover image or its video"""


class MediaType(StrEnum):
    PNG = "image/png"
    """A PNG image"""

    JPEG = "image/jpeg"
    """A JPEG image"""

    WEBP = "image/webp"
    """A WebP image"""

    MP4 = "video/mp4"
    """An MP4 video; the site plays it muted"""

    @property
    def slot(self) -> MediaSlot:
        """Which of a project's media a file of this type can be"""
        return "video" if self is MediaType.MP4 else "image"

    @property
    def max_bytes(self) -> int:
        """10 MB for an image, 200 MB for a video"""
        return (200 if self is MediaType.MP4 else 10) * 1024 * 1024

    @property
    def too_large(self) -> str:
        """Why a file over max_bytes is refused"""
        return f"{self.slot.capitalize()}s can be up to {self.max_bytes // (1024 * 1024)} MB"

    @property
    def extension(self) -> str:
        """The public file's extension, so the CDN serves it as its type"""
        return ".jpg" if self is MediaType.JPEG else f".{self.split('/')[1]}"


__all__ = ["MediaSlot", "MediaType"]
