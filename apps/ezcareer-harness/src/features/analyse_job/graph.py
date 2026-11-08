from datetime import UTC, datetime
from typing import Annotated

import httpx
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.agents import build_agent, load_agents
from src.agents.job_finder import JobFinderState
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
from src.shared.checks import CheckError, CheckRound, check_round
from src.shared.profile import Profile
from src.tools import read_profile_facts


class AnalyseJobInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    url: HttpUrl
    """The posting the user pasted"""

    profile: Profile
    """The user's facts and preferences"""


class AnalyseJobOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    analysis: JobAnalysis | None = None
    """How well the posting fits, for ops"""


class AnalyseJobState(AnalyseJobInput, AnalyseJobOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    lines: list[PostingLine] = Field(default_factory=list)
    """The posting's numbered lines"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The agent's conversation across check rounds"""

    requirements: JobRequirements | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


async def _fetch(state: AnalyseJobState) -> dict:
    """Fetch the posting and hand its lines to the agent as untrusted text"""
    try:
        lines = await fetch_posting(str(state.url))
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
            **state.requirements.model_dump(),
            url=state.url,
            lines=state.lines,
            filters=hard_filters(
                state.requirements.terms, state.profile, datetime.now(UTC).date()
            ),
        )
    }


def build_graph(
    model: BaseChatModel | None = None, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The analyse-job graph with the agent and configurations the settings name;
    model replaces the agent's LLM; checkpointer keeps its runs"""
    settings = get_settings()
    configurations = settings.graph_profile("analyse-job").load(
        AnalyseJobConfigurations
    )
    checks = [CHECKS[name] for name in configurations.checks]
    agent = build_agent(
        load_agents(settings.agents)["job-finder"],
        answers=(JobRequirements,),
        tools=(read_profile_facts,),
        state_schema=JobFinderState,
        model=model,
    )

    async def run_agent(state: AnalyseJobState) -> dict:
        result = await agent.ainvoke(
            {
                "messages": state.messages,
                "facts": state.profile.facts,
                "preferences": state.profile.preferences,
            },
            {"recursion_limit": configurations.agent_recursion_limit},
        )
        return {
            "messages": result["messages"],
            "requirements": result["structured_response"],
        }

    def check(state: AnalyseJobState) -> CheckRound:
        return check_round(
            [
                error
                for check in checks
                for error in check(state.requirements, state.lines, state.profile.facts)
            ]
        )

    graph = StateGraph(
        AnalyseJobState, input_schema=AnalyseJobInput, output_schema=AnalyseJobOutput
    )
    graph.add_node("fetch", _fetch)
    graph.add_node("agent", run_agent)
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
