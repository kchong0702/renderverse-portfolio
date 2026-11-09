from datetime import UTC, datetime
from typing import Annotated

import httpx
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field

from src.agents import AgentOverride
from src.core.config import get_settings
from src.core.errors import ExecuteError
from src.features.analyse_job.configurations import CHECKS, AnalyseJobConfigurations
from src.features.analyse_job.filters import hard_filters
from src.features.analyse_job.nodes import fetch_posting
from src.features.analyse_job.schemas import (
    JobAnalysis,
    JobRequirements,
    PostingLine,
)
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.profile import Preferences, Profile, ProfileFact
from src.shared.url import Url


class AnalyseJobInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    url: Url
    """The posting the user pasted"""

    facts: list[ProfileFact]
    """The user's profile facts"""

    preferences: Preferences = Field(default_factory=Preferences)
    """What the user wants from a job"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The user's note, if any, then the agent's conversation across check rounds"""


class AnalyseJobOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    analysis: JobAnalysis | None = None
    """How well the posting fits, for ops"""


class AnalyseJobState(AnalyseJobInput, AnalyseJobOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    lines: list[PostingLine] = Field(default_factory=list)
    """The posting's numbered lines"""

    structured_response: JobRequirements | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


async def _fetch(state: AnalyseJobState) -> dict:
    """Fetch the posting and hand the agent its lines as untrusted text"""
    try:
        lines = await fetch_posting(state.url)
    except httpx.HTTPError as error:
        raise ExecuteError(f"Couldn't fetch the posting: {error}") from error
    if not lines:
        raise ExecuteError("The posting page has no text")
    posting = "\n".join(f"[{line.id}] {line.text}" for line in lines)
    return {
        "lines": lines,
        "messages": [
            HumanMessage(
                f"Analyse this job posting.\n\n<posting untrusted>\n{posting}\n</posting>"
            )
        ],
    }


def _output(state: AnalyseJobState) -> dict:
    """Add the posting, the hard filters and the computed fit for ops"""
    return {
        "analysis": JobAnalysis(
            **state.structured_response.model_dump(),
            url=state.url,
            lines=state.lines,
            filters=hard_filters(
                state.structured_response.terms,
                Profile(facts=state.facts, preferences=state.preferences),
                datetime.now(UTC).date(),
            ),
        )
    }


def build_graph(
    agent: CompiledStateGraph, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The analyse-job workflow run on agent, with the configurations the
    settings name; checkpointer keeps its runs"""
    settings = get_settings()
    configurations = settings.graph_profile("analyse-job").load(
        AnalyseJobConfigurations
    )
    checks = [CHECKS[name] for name in configurations.checks]

    def check(state: AnalyseJobState) -> CheckRound:
        if state.structured_response is None:
            return check_round(
                [
                    CheckError(
                        rule=CheckRule.NO_ANSWER,
                        at="answer",
                        message="Reply with a JobRequirements",
                    )
                ]
            )
        return check_round(
            [
                error
                for check in checks
                for error in check(state.structured_response, state.lines, state.facts)
            ]
        )

    graph = StateGraph(
        AnalyseJobState, input_schema=AnalyseJobInput, output_schema=AnalyseJobOutput
    )
    graph.add_node("fetch", _fetch)
    graph.add_node(
        "agent",
        agent.with_config(AgentOverride(response_format=JobRequirements).config()),
    )
    graph.add_node("check", check)
    graph.add_node("output", _output)
    graph.add_edge(START, "fetch")
    graph.add_edge("fetch", "agent")
    graph.add_edge("agent", "check")
    graph.add_conditional_edges(
        "check", lambda state: "agent" if state.errors else "output"
    )
    graph.add_edge("output", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit, metadata={"flow": "analyse-job"}
    )
