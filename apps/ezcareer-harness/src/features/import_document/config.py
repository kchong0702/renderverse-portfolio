from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ImportConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, use_attribute_docstrings=True
    )

    model: str = "claude-sonnet-5-5"
    """Anthropic model that reads the résumé"""

    prompt: Path = Path(__file__).parent / "prompts" / "structure.md"
    """Mustache template of the structure call's system prompt"""

    soffice: str = "soffice"
    """LibreOffice command that converts Word files"""
