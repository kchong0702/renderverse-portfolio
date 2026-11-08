from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.features.write_document.checks import check_changeset

CHECKS = {"changeset": check_changeset}
"""Every check the write-document configurations.yaml may turn on, by name"""


class WriteDocumentConfigurations(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    checks: list[Literal["changeset"]]
    """Checks run on each changeset"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take across all check rounds"""

    agent_recursion_limit: int = Field(gt=0)
    """Steps one agent turn may take"""

    page_fit_trims: int = Field(ge=0)
    """Bullets page-fit may delete to keep the page count"""
