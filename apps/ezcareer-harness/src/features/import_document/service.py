import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.features.import_document.config import ImportConfig
from src.features.import_document.errors import ImportFailed
from src.features.import_document.graph import build_graph
from src.features.import_document.schemas import (
    ImportInput,
    ImportOutput,
    ImportResult,
    ImportTask,
)
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
                "metadata": {"import_config_hash": config.hash},
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


def build_task_graph(
    config: ImportConfig,
    artifacts: ArtifactService,
    model: BaseChatModel | None = None,
) -> CompiledStateGraph:
    """A one-node graph for the A2A server: imports the input's file and returns
    the ImportResult as JSON under result"""

    async def run(task: ImportTask) -> ImportOutput:
        """Runs the import with the graph's config, client and model"""
        result = await run_import(task["file"], config, artifacts, model)
        return {"result": result.model_dump(mode="json")}

    graph = StateGraph(
        ImportOutput, input_schema=ImportInput, output_schema=ImportOutput
    )
    graph.add_node("run", run)
    graph.add_edge(START, "run")
    graph.add_edge("run", END)
    return graph.compile()
