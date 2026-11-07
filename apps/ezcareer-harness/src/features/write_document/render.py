from pathlib import Path

import httpx
import yaml
from document_schema import AnyDocument, FileHash, Report

from src.core.errors import FlowError
from src.features.write_document.state import Render
from src.shared.clients.artifact_service import ArtifactService


def render_with(artifacts: ArtifactService, templates: Path) -> Render:
    """A render function that prints through artifact-service with the
    document's template spec from templates"""

    async def render(document: AnyDocument, assets: dict[FileHash, bytes]) -> Report:
        """Prints the document and returns its Report"""
        template = yaml.safe_load(
            (templates / f"{document.design.template}.yaml").read_text()
        )
        try:
            return (await artifacts.render(document, template, assets)).report
        except httpx.HTTPError as error:
            raise FlowError(f"Couldn't print the edited document: {error}") from error

    return render
