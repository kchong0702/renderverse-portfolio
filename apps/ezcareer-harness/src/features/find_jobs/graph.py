from typing import Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AnyMessage, HumanMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field

from src.agents import Workflow, build_agent, load_agents
from src.agents.job_finder import JobFinderState
from src.core.config import get_settings
from src.features.find_jobs.adapters import SearchProtocol
from src.features.find_jobs.configurations import CHECKS, FindJobsConfigurations
from src.features.find_jobs.ranking import matched_jobs
from src.features.find_jobs.schemas import JobPosting, MatchedJob, RankedJobs
from src.features.find_jobs.tools import search_jobs_tool
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.factory import Factory
from src.shared.profile import Profile
from src.tools import read_profile_facts


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


def build_graph(
    job_sources: Factory[SearchProtocol],
    model: BaseChatModel | None = None,
    checkpointer: Checkpointer = None,
) -> CompiledStateGraph:
    """The find-jobs graph with the agent, configurations and job sources the
    settings name; model replaces the agent's LLM; checkpointer keeps its runs"""
    settings = get_settings()
    configurations = settings.graph_profile("find-jobs").load(FindJobsConfigurations)
    checks = [CHECKS[name] for name in configurations.checks]
    agent = build_agent(
        load_agents(settings.agents)["job-finder"],
        answers=(RankedJobs,),
        tools=(
            read_profile_facts,
            search_jobs_tool(
                [job_sources.create(name) for name in settings.job_sources]
            ),
        ),
        state_schema=JobFinderState,
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
            Workflow(response_format=RankedJobs).config(
                {"recursion_limit": configurations.agent_recursion_limit}
            ),
        )
        return {
            "messages": result["messages"],
            "ranked": result.get("structured_response"),
        }

    def check(state: FindJobsState) -> CheckRound:
        postings = _postings(state.messages)
        if state.ranked is None:
            return check_round(
                [
                    CheckError(
                        rule=CheckRule.NO_ANSWER,
                        at="answer",
                        message="Answer by calling the RankedJobs tool",
                    )
                ]
            )
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
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit, metadata={"flow": "find-jobs"}
    )
