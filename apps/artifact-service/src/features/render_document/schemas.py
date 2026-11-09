from base64 import b64encode
from hashlib import sha256
from typing import Annotated, Self

from document_schema import AnyDocument, FileHash, Report
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

from src.shared.templates import templates


class RenderRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
        val_json_bytes="base64",
    )

    document: AnyDocument
    """The document to print"""

    assets: dict[FileHash, bytes] = Field(default_factory=dict)
    """Bytes of each file the document uses, base64 in JSON, by hash"""

    @model_validator(mode="after")
    def _assets_and_template_match(self) -> Self:
        """Rejects missing or wrong bytes, and a template that is unknown or for
        another kind"""
        if missing := set(self.document.assets) - set(self.assets):
            raise ValueError(f"assets have no bytes: {sorted(missing)}")
        if wrong := [
            k for k, data in self.assets.items() if sha256(data).hexdigest() != k
        ]:
            raise ValueError(f"bytes do not hash to {wrong}")
        template = self.document.design.template
        if template not in templates():
            raise ValueError(f"no template {template}")
        if self.document.kind not in templates()[template].kinds:
            raise ValueError(f"{template} does not lay out a {self.document.kind}")
        return self


class RenderResponse(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    artifact: Annotated[
        bytes,
        PlainSerializer(
            lambda artifact: b64encode(artifact).decode(),
            return_type=str,
            when_used="json",
        ),
    ]
    """The printed PDF, base64 in JSON"""

    report: Report
    """How the pages came out"""
