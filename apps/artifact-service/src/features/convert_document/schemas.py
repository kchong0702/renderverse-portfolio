from base64 import b64encode
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer


class ConvertRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        val_json_bytes="base64",
    )

    file: bytes
    """The Word or PDF file, base64 in JSON"""


class ConvertResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    pdf: Annotated[
        bytes,
        PlainSerializer(
            lambda pdf: b64encode(pdf).decode(), return_type=str, when_used="json"
        ),
    ]
    """The file as a PDF, base64 in JSON"""
