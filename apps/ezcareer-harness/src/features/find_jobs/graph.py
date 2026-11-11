from typing import Annotated

from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field

from src.adapters.job_sources import SearchResult
from src.agents import AgentOverride
from src.core.config import get_settings
from src.features.find_jobs.configurations import CHECKS, FindJobsConfigurations
from src.features.find_jobs.ranking import matched_jobs
from src.features.find_jobs.schemas import MatchedJob, RankedJobs
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.jobs import JobPosting, JobSearch, Quota
from src.shared.profile import Preferences, Profile, ProfileFact, require_facts


class FindJobsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    facts: list[ProfileFact]
    """The user's profile facts"""

    preferences: Preferences = Field(default_factory=Preferences)
    """What the user wants from a job"""

    search: JobSearch | None = None
    """The user's own search, whose fields replace the agent's in each search"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The user's note, if any, then the agent's conversation across check rounds"""


class FindJobsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    jobs: list[MatchedJob] = Field(default_factory=list)
    """Ranked jobs with their computed fit, for ops"""

    quota: Quota | None = None
    """JSearch's requests left and allowed after the last search, if it said"""


class FindJobsState(FindJobsInput, FindJobsOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    structured_response: RankedJobs | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


def _searches(messages: list[AnyMessage]) -> list[SearchResult]:
    """What each search_jobs call in the conversation returned"""
    return [
        message.artifact
        for message in messages
        if isinstance(message, ToolMessage)
        and message.name == "search_jobs"
        and message.artifact
    ]


def _postings(messages: list[AnyMessage]) -> list[JobPosting]:
    """Every posting search_jobs returned in the conversation"""
    return [posting for result in _searches(messages) for posting in result.postings]


def _brief(state: FindJobsState) -> dict:
    """Ask the agent for jobs, handing it the user's preferences and own search"""
    require_facts(state.facts)
    return {
        "messages": [
            HumanMessage(
                f"Find jobs for me. My preferences: {state.preferences.model_dump_json()}."
                + (
                    f" My search: {state.search.model_dump_json(exclude_none=True)}."
                    " search_jobs uses its fields over yours."
                    if state.search
                    else ""
                )
            )
        ]
    }


def _output(state: FindJobsState) -> dict:
    """Join the ranked jobs with their postings, highest fit first, and add the
    quota the last search reported"""
    quotas = [result.quota for result in _searches(state.messages) if result.quota]
    return {
        "jobs": matched_jobs(state.structured_response, _postings(state.messages)),
        "quota": quotas[-1] if quotas else None,
    }


def build_graph(
    agent: CompiledStateGraph,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    """The find-jobs workflow run on agent, with the configurations the settings
    name; checkpointer keeps its runs"""
    configurations = (
        get_settings().graph_profile("find-jobs").load(FindJobsConfigurations)
    )
    checks = [CHECKS[name] for name in configurations.checks]

    def check(state: FindJobsState) -> CheckRound:
        if state.structured_response is None:
            return check_round(
                [
                    CheckError(
                        rule=CheckRule.NO_ANSWER,
                        at="answer",
                        message="Reply with a RankedJobs",
                    )
                ]
            )
        postings = _postings(state.messages)
        return check_round(
            [
                error
                for check in checks
                for error in check(
                    state.structured_response,
                    postings,
                    Profile(facts=state.facts, preferences=state.preferences),
                )
            ]
        )

    graph = StateGraph(
        FindJobsState, input_schema=FindJobsInput, output_schema=FindJobsOutput
    )
    graph.add_node("brief", _brief)
    graph.add_node(
        "agent",
        agent.with_config(AgentOverride(response_format=RankedJobs).config()),
    )
    graph.add_node("check", check)
    graph.add_node("output", _output)
    graph.add_edge(START, "brief")
    graph.add_edge("brief", "agent")
    graph.add_edge("agent", "check")
    graph.add_conditional_edges(
        "check", lambda state: "agent" if state.errors else "output"
    )
    graph.add_edge("output", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit, metadata={"flow": "find-jobs"}
    )
