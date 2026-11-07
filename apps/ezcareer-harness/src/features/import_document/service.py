from pathlib import Path
from typing import Any

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from src.core.config import get_settings
from src.features.import_document.config import ImportConfig
from src.features.import_document.errors import ImportFailed
from src.features.import_document.graph import build_graph
from src.features.import_document.schemas import ImportInput, ImportResult
from src.features.import_document.state import ImportContext
from src.shared.clients.artifact_service import ArtifactService
from src.shared.extraction import UnreadableFile


async def run_import(
    file: bytes,
    config: ImportConfig,
    artifacts: ArtifactService,
    model: BaseChatModel | None = None,
) -> ImportResult:
    """Imports an uploaded résumé; fails when it can't be read, never passes the
    checks or can't be printed. model defaults to the config's"""
    try:
        state = await build_graph().ainvoke(
            {"file": file},
            config={
                "recursion_limit": config.recursion_limit,
                "metadata": {"flow": "import", "harness_hash": config.hash},
            },
            context=ImportContext(
                config=config,
                model=model or ChatAnthropic(model=config.model),
                artifacts=artifacts,
            ),
        )
    except UnreadableFile as error:
        raise ImportFailed(str(error)) from error
    except GraphRecursionError as error:
        raise ImportFailed("couldn't read this file") from error
    except httpx.HTTPError as error:
        raise ImportFailed("couldn't print the draft; try again") from error
    if "document" not in state:
        raise ImportFailed("couldn't read this file")
    return ImportResult(
        document=state["document"],
        pdf=state["pdf"],
        report=state["report"],
        lines=state["lines"],
        rounds=state["rounds"],
        config_hash=config.hash,
    )


async def import_task(
    task: ImportInput, harness: Path = Path(__file__).parent / "harness"
) -> dict[str, Any]:
    """Runs one import with a harness folder, the bundled one by default, returning
    the result as JSON"""
    settings = get_settings().artifact_service
    async with httpx.AsyncClient(
        base_url=settings.url, timeout=settings.timeout_s
    ) as client:
        result = await run_import(
            task.file, ImportConfig.load(harness), ArtifactService(client)
        )
    return result.model_dump(mode="json")
