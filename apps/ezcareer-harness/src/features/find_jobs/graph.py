from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel, ConfigDict, Field

from src.agents import build_agent, load_agents
from src.core.config import get_settings
from src.features.find_jobs.graph_profile import CHECKS, FindJobsProfile
from src.features.find_jobs.ranking import matched_jobs
from src.features.find_jobs.schemas import JobPosting, MatchedJob, RankedJobs
from src.features.find_jobs.tools import JobSearchState, search_jobs
from src.shared.checks import CheckError, CheckRound, check_round
from src.shared.models import Profile
from src.shared.tools import read_profile_facts


class FindJobsInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    profile: Profile
    """The user's facts and preferences"""


class FindJobsOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    jobs: list[MatchedJob] = Field(default_factory=list)
    """Ranked jobs with their computed fit, for ops"""


class FindJobsState(FindJobsInput, FindJobsOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The agent's conversation across check rounds"""

    ranked: RankedJobs | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


def _postings(messages: list[AnyMessage]) -> list[JobPosting]:
    """Every posting search_jobs returned in the conversation"""
    return [
        posting
        for message in messages
        if isinstance(message, ToolMessage) and message.name == "search_jobs"
        for posting in message.artifact or []
    ]


def _output(state: FindJobsState) -> dict:
    """Join the ranked jobs with their postings, highest fit first"""
    return {"jobs": matched_jobs(state.ranked, _postings(state.messages))}


def build_graph(model: BaseChatModel | None = None) -> CompiledStateGraph:
    """The find-jobs graph with the agent and graph profile the settings name;
    model replaces the agent's LLM"""
    settings = get_settings()
    graph_profile = settings.graph_profile("find-jobs").load(FindJobsProfile)
    checks = [CHECKS[name] for name in graph_profile.checks]
    agent = build_agent(
        load_agents(settings.agents)["job-finder"],
        response_format=RankedJobs,
        tools=(read_profile_facts, search_jobs),
        state_schema=JobSearchState,
        model=model,
    )

    async def run_agent(state: FindJobsState) -> dict:
        preferences = state.profile.preferences.model_dump_json()
        messages = state.messages or [
            HumanMessage(f"Find jobs for me. My preferences: {preferences}")
        ]
        result = await agent.ainvoke(
            {
                "messages": messages,
                "facts": state.profile.facts,
                "preferences": state.profile.preferences,
            },
            {"recursion_limit": graph_profile.agent_recursion_limit},
        )
        return {
            "messages": result["messages"],
            "ranked": result["structured_response"],
        }

    def check(state: FindJobsState) -> CheckRound:
        postings = _postings(state.messages)
        return check_round(
            [
                error
                for check in checks
                for error in check(state.ranked, postings, state.profile)
            ]
        )

    graph = StateGraph(
        FindJobsState, input_schema=FindJobsInput, output_schema=FindJobsOutput
    )
    graph.add_node("agent", run_agent)
    graph.add_node("check", check)
    graph.add_node("output", _output)
    graph.add_edge(START, "agent")
    graph.add_edge("agent", "check")
    graph.add_conditional_edges(
        "check", lambda state: "agent" if state.errors else "output"
    )
    graph.add_edge("output", END)
    return graph.compile().with_config(
        recursion_limit=graph_profile.recursion_limit, metadata={"flow": "find-jobs"}
    )
