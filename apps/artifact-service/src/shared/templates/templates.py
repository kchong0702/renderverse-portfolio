from functools import cache

import yaml
from document_schema import TemplateId, TemplateSpec

from src.core.config import get_settings


@cache
def templates() -> dict[TemplateId, TemplateSpec]:
    """The renderer's template specs by id, read once"""
    return {
        spec.id: spec
        for spec in (
            TemplateSpec.model_validate(yaml.safe_load(path.read_text()))
            for path in sorted(get_settings().renderer.templates.glob("*.yaml"))
        )
    }
