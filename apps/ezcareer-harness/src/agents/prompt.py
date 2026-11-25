import re
from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic_core import PydanticCustomError


class PromptMeta(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        use_attribute_docstrings=True,
    )

    version: str
    """The prompt's version, raised with each change"""

    description: str
    """What the prompt is for"""

    author: str
    """Who last changed it"""

    date: date
    """When it last changed"""

    status: Literal["active", "archived"]
    """active is in use; archived is kept for its history and refused"""

    @field_validator("version", mode="before")
    @classmethod
    def _quoted(cls, version: object) -> str:
        """Refuses a version YAML read as a number, which turns 1.10 into 1.1"""
        if not isinstance(version, str):
            raise PydanticCustomError(
                "unquoted_version", 'quote the version, as in version: "1.0"'
            )
        return version


def _split(path: Path) -> tuple[PromptMeta, str]:
    """The file's YAML front matter as a PromptMeta, and the text after it"""
    found = re.fullmatch(r"---\n(.*?)\n---(?:\n(.*))?", path.read_text(), re.DOTALL)
    if found is None:
        raise ValueError(f"{path} doesn't start with --- front matter")
    return PromptMeta.model_validate(yaml.safe_load(found[1])), found[2] or ""


def is_active(path: Path) -> bool:
    """Whether the prompt file's front matter says it is in use"""
    return _split(path)[0].status == "active"


def read_prompt(path: Path) -> str:
    """The prompt text after the file's YAML front matter, which must be a
    PromptMeta whose status is active"""
    header, text = _split(path)
    if header.status == "archived":
        raise ValueError(f"{path} is archived")
    return text.strip()
