from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langgraph.errors import GraphRecursionError

from src.features.import_document.config import ImportConfig
from src.features.import_document.errors import ImportFailed
from src.features.import_document.graph import build_graph
from src.features.import_document.state import ImportContext, ImportState
from src.shared.extraction import UnreadableFile


async def run_import(
    file: bytes, config: ImportConfig, model: BaseChatModel | None = None
) -> ImportState:
    """Imports an uploaded résumé, failing when it can't be read or never passes
    the checks; model defaults to the config's"""
    try:
        return await build_graph().ainvoke(
            {"file": file},
            config={
                "recursion_limit": config.recursion_limit,
                "metadata": {"import_config": config.version},
            },
            context=ImportContext(
                config=config, model=model or ChatAnthropic(model=config.model)
            ),
        )
    except (UnreadableFile, GraphRecursionError) as error:
        raise ImportFailed("couldn't read this file") from error
