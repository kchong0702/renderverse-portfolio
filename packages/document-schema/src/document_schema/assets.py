from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated

from pydantic import StringConstraints

from document_schema.base import SchemaModel

Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]

# `src="asset:<sha256>"` or `url(asset:<sha256>)`
ASSET_REF = re.compile(r"""(?<=["'(])asset:([0-9a-f]{64})""")


class MediaType(StrEnum):
    WOFF2 = "font/woff2"
    PNG = "image/png"
    JPEG = "image/jpeg"
    WEBP = "image/webp"


class Asset(SchemaModel):
    media_type: MediaType
    """Kind of file, limited to what the renderer can embed in a page"""

    uri: str
    """Where the owner stores the asset, opaque to the schema"""
