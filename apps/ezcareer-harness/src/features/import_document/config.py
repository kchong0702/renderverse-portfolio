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

    model: str
    """Anthropic model that reads the résumé"""

    prompt: str
    """Mustache template of the structure call's system prompt"""

    rounds: int = Field(ge=1)
    """Replies the verifier checks before the import gives up"""

    checks: tuple[Check, ...]
    """Checks the verifier runs on each reply, by name"""

    soffice: str = "soffice"
    """LibreOffice command that converts Word files"""

    templates: Path = Path(__file__).parents[5] / "packages/document-renderer/templates"
    """Folder of the renderer's <id>.yaml template specs"""

    @classmethod
    def load(cls, folder: Path = Path(__file__).parent / "harness") -> "ImportConfig":
        """Reads a harness folder: harness.yaml for the settings, structure.md for
        the prompt"""
        settings = yaml.safe_load((folder / "harness.yaml").read_text())
        return cls(prompt=(folder / "structure.md").read_text(), **settings)

    @property
    def recursion_limit(self) -> int:
        """Graph steps for every round, a safety net behind verify's own stop:
        LangGraph's input step, extract, then structure and verify each round"""
        return 2 * self.rounds + 2

    @property
    def hash(self) -> str:
        """Sha256 of the settings that shape the reply, prompt included"""
        settings = self.model_dump_json(exclude={"soffice", "templates"})
        return hashlib.sha256(settings.encode()).hexdigest()

    def template(self, template_id: str) -> dict[str, Any]:
        """The spec of one template, as the renderer's YAML holds it"""
        return yaml.safe_load((self.templates / f"{template_id}.yaml").read_text())
