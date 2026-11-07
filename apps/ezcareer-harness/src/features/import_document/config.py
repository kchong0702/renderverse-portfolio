import hashlib
from pathlib import Path
from typing import Any

import yaml
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

    templates: Path = Path(__file__).parents[5] / "packages/document-renderer/templates"
    """Folder of the renderer's <id>.yaml template specs"""

    @property
    def version(self) -> str:
        """Hash of the settings that shape the reply, prompt included, recorded
        with every run"""
        settings = self.model_dump_json(exclude={"soffice", "templates"})
        return hashlib.sha256(settings.encode()).hexdigest()[:12]

    def template(self, template_id: str) -> dict[str, Any]:
        """The spec of one template, as the renderer's YAML holds it"""
        return yaml.safe_load((self.templates / f"{template_id}.yaml").read_text())
