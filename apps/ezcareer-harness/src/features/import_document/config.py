import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.shared.checks.resume import Check


class ImportConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    model: str = "claude-sonnet-5-5"
    """Anthropic model that reads the résumé"""

    prompt: str = Field(
        default_factory=lambda: (
            Path(__file__).parent / "prompts" / "structure.md"
        ).read_text()
    )
    """Mustache template of the structure call's system prompt"""

    soffice: str = "soffice"
    """LibreOffice command that converts Word files"""

    recursion_limit: int = Field(10, ge=3)
    """Graph steps before the import gives up; each verifier round takes two"""

    checks: tuple[Check, ...] = tuple(Check)
    """Checks the verifier runs on each reply"""

    @property
    def version(self) -> str:
        """Hash of these settings, prompt included, recorded with every run"""
        return hashlib.sha256(self.model_dump_json().encode()).hexdigest()[:12]
