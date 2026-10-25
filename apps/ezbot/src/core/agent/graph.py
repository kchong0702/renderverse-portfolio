from __future__ import annotations

import asyncio
from collections.abc import Sequence
from pathlib import Path

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelFallbackMiddleware
from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from src.core.agent.classifier.base import IntentClassifier
from src.core.agent.middlewares.system_prompt import system_prompt_middleware
from src.core.agent.state import EzbotState
from src.core.config import IntentSettings
from src.infrastructure.observability.logging import get_logger
from src.shared.schemas.agent import EzbotContext
from src.shared.schemas.intent import Intent

_logger = get_logger(__name__)

MODEL_NODE_NAME = "model"
"""Node `create_agent` runs the chat model in, whose tokens are streamed"""

PROMPT_PATH = Path(__file__).parent / "prompts" / "ezbot.yaml"


def _classify_intent(classifier: IntentClassifier, timeout_s: float):
    async def classify_intent(state: EzbotState) -> dict[str, Intent | None]:
        try:
            intent = await asyncio.wait_for(
                classifier.classify(state["messages"]), timeout=timeout_s
            )
        except TimeoutError:
            _logger.warning("Intent classification timed out")
            intent = None
        except Exception:
            _logger.exception("Intent classification failed")
            intent = None
        return {"intent": intent}

    return classify_intent


def build_ezbot_graph(
    models: Sequence[BaseChatModel],
    *,
    intent: IntentSettings | None = None,
    classifier: IntentClassifier | None = None,
    system_prompt: str | None = None,
) -> CompiledStateGraph:
    if not models:
        raise ValueError("build_ezbot_graph needs at least one model")
    primary, *fallbacks = models
    middleware: list[AgentMiddleware] = []
    if system_prompt is None:
        if intent is None:
            raise ValueError("build_ezbot_graph needs intent settings for ezbot.yaml")
        middleware.append(
            system_prompt_middleware(PROMPT_PATH, intent_enabled=intent.enabled)
        )
    if fallbacks:
        middleware.append(ModelFallbackMiddleware(*fallbacks))
    agent = create_agent(
        primary,
        system_prompt=system_prompt,
        middleware=middleware,
        context_schema=EzbotContext,
        name="agent",
    )

    graph = StateGraph(EzbotState, context_schema=EzbotContext)
    graph.add_node("agent", agent)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", END)
    if classifier is not None:
        if intent is None:
            raise ValueError("build_ezbot_graph needs intent settings for a classifier")
        graph.add_node(
            "classify_intent", _classify_intent(classifier, intent.timeout_s)
        )
        graph.add_edge(START, "classify_intent")
        graph.add_edge("classify_intent", END)
    return graph.compile(name="ezbot")


__all__ = [
    "MODEL_NODE_NAME",
    "PROMPT_PATH",
    "build_ezbot_graph",
]
