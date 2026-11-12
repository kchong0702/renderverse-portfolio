from functools import partial

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import ConfigDict, Field

from src.agents import AgentOverride
from src.core.config import get_settings
from src.features.write_networking.checks import (
    check_citations,
    check_coverage,
    check_form,
)
from src.features.write_networking.configurations import WriteNetworkingConfigurations
from src.features.write_networking.schemas import NetworkingCopy, WriteNetworkingInput
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.profile import require_facts

CHECKS = {
    "coverage": check_coverage,
    "citations": check_citations,
    "form": check_form,
}
"""Every check the write-networking configurations.yaml may turn on, by name"""


class WriteNetworkingState(WriteNetworkingInput, NetworkingCopy):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    structured_response: NetworkingCopy | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


def _brief(
    state: WriteNetworkingState, configurations: WriteNetworkingConfigurations
) -> dict:
    """Ask the agent for the fields to write, aimed at the user's jobs, within
    their caps"""
    require_facts(state.facts)
    asked = [
        f"the {field}"
        if field in ("headline", "summary")
        else f"a description of fact:{field}"
        for field in state.fields()
    ]
    aim = f"jobs like: {state.aim}" if state.aim else "the jobs my facts point to"
    return {
        "messages": [
            HumanMessage(
                "Write my networking copy, to paste into job portals and networking"
                f" sites, aimed at {aim}.\n\n"
                + ("Write " if state.only is None else "Write only ")
                + ", ".join(asked)
                + ".\n\nCaps: the headline at most"
                f" {configurations.max_headline_chars} characters, the summary at most"
                f" {configurations.max_summary_chars}, each description at most"
                f" {configurations.max_description_chars}."
            )
        ]
    }


def _check(
    state: WriteNetworkingState, configurations: WriteNetworkingConfigurations
) -> CheckRound:
    """Run the configured checks on the agent's answer, or ask for one"""
    if state.structured_response is None:
        return check_round(
            [
                CheckError(
                    rule=CheckRule.NO_ANSWER,
                    at="answer",
                    message="Reply with a NetworkingCopy",
                )
            ]
        )
    return check_round(
        [
            error
            for name in configurations.checks
            for error in CHECKS[name](state.structured_response, state, configurations)
        ]
    )


def _output(state: WriteNetworkingState) -> dict:
    """Only the fields asked for"""
    fields, copy = state.fields(), state.structured_response
    return {
        "headline": copy.headline if "headline" in fields else None,
        "summary": copy.summary if "summary" in fields else None,
        "descriptions": [d for d in copy.descriptions if d.fact in fields],
    }


def build_graph(
    agent: CompiledStateGraph, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The write-networking workflow run on agent, with the configurations the
    settings name; checkpointer keeps its runs"""
    configurations = (
        get_settings()
        .graph_profile("write-networking")
        .load(WriteNetworkingConfigurations)
    )
    graph = StateGraph(
        WriteNetworkingState,
        input_schema=WriteNetworkingInput,
        output_schema=NetworkingCopy,
    )
    graph.add_node("brief", partial(_brief, configurations=configurations))
    graph.add_node(
        "agent",
        agent.with_config(
            AgentOverride(
                response_format=NetworkingCopy,
                tools=frozenset({"read_profile_facts"}),
            ).config()
        ),
    )
    graph.add_node("check", partial(_check, configurations=configurations))
    graph.add_node("output", _output)
    graph.add_edge(START, "brief")
    graph.add_edge("brief", "agent")
    graph.add_edge("agent", "check")
    graph.add_conditional_edges(
        "check", lambda state: "agent" if state.errors else "output"
    )
    graph.add_edge("output", END)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit,
        metadata={"flow": "write-networking"},
    )
