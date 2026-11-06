from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from src.features.import_document.config import ImportConfig
from src.features.import_document.errors import ImportFailed
from src.features.import_document.graph import build_graph
from src.features.import_document.schemas import ImportResult
from src.features.import_document.state import ImportContext
from src.shared.clients import ArtifactService
from src.shared.extraction import UnreadableFile


async def run_import(
    file: bytes,
    config: ImportConfig,
    artifacts: ArtifactService,
    model: BaseChatModel | None = None,
) -> ImportResult:
    """Imports an uploaded résumé, failing when it can't be read or never passes
    the checks; model defaults to the config's"""
    try:
        state = await build_graph().ainvoke(
            {"file": file},
            config={
                "recursion_limit": config.recursion_limit,
                "metadata": {"import_config": config.version},
            },
            context=ImportContext(
                config=config,
                model=model or ChatAnthropic(model=config.model),
                artifacts=artifacts,
            ),
        )
    except (UnreadableFile, GraphRecursionError) as error:
        raise ImportFailed("couldn't read this file") from error
    return ImportResult(
        document=state["document"],
        pdf=state["pdf"],
        report=state["report"],
        lines=state["lines"],
        rounds=state["rounds"],
        config_version=config.version,
    )
