from __future__ import annotations

from base64 import b64encode
from typing import Annotated

from document_schema import Report
from pydantic import BaseModel, ConfigDict, PlainSerializer


class Render(BaseModel):
    model_config = ConfigDict(val_json_bytes="base64")

    artifact: Annotated[
        bytes,
        PlainSerializer(
            lambda artifact: b64encode(artifact).decode(),
            return_type=str,
            when_used="json",
        ),
    ]
    """The printed PDF, standard base64 in JSON as browsers' atob reads it"""

    report: Report
    """How the pages came out: page count, last page fill and warnings"""


__all__ = ["Render"]
