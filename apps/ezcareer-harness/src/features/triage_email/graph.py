from datetime import date
from typing import Annotated

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field

from src.agents import AgentOverride
from src.core.config import get_settings
from src.features.triage_email.configurations import TriageEmailConfigurations
from src.features.triage_email.enums import ThreadState
from src.features.triage_email.matching import matched_application
from src.features.triage_email.schemas import Application, EmailReading, Interview
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.email import EmailThread, untrusted_thread


class TriageEmailInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    thread: EmailThread
    """The email thread to triage"""

    applications: list[Application] = Field(default_factory=list)
    """The user's applications the thread may be about"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The user's note, if any, then the agent's conversation across check rounds"""


class TriageEmailOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    state: ThreadState | None = None
    """What the thread asks of the user; None only before the run ends"""

    application_id: str | None = None
    """The application the thread is about, if one clearly is"""

    decide_by: date | None = None
    """The date an offer must be answered by, if it names one"""

    interview: Interview | None = None
    """The interview the thread confirms, if it confirms one"""


class TriageEmailState(TriageEmailInput, TriageEmailOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    structured_response: EmailReading | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


def _brief(state: TriageEmailState) -> dict:
    """Hand the agent the thread as untrusted text"""
    return {
        "messages": [
            HumanMessage(
                f"Triage this email thread.\n\n{untrusted_thread(state.thread)}"
            )
        ]
    }


def _check(state: TriageEmailState) -> CheckRound:
    """Send the agent back when it ended without an EmailReading"""
    if state.structured_response is None:
        return check_round(
            [
                CheckError(
                    rule=CheckRule.NO_ANSWER,
                    at="answer",
                    message="Reply with an EmailReading",
                )
            ]
        )
    return check_round([])


def _output(state: TriageEmailState) -> dict:
    """The agent's reading, keeping a deadline only for an offer and an interview
    only when one is confirmed, with the application matched in code"""
    reading = state.structured_response
    return {
        "state": reading.state,
        "application_id": matched_application(state.thread, state.applications),
        "decide_by": reading.decide_by if reading.state == ThreadState.OFFER else None,
        "interview": reading.interview
        if reading.state == ThreadState.INTERVIEW
        else None,
    }


def build_graph(
    agent: CompiledStateGraph, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The triage-email workflow run on agent, with the configurations the settings
    name; checkpointer keeps its runs"""
    configurations = (
        get_settings().graph_profile("triage-email").load(TriageEmailConfigurations)
    )
    graph = StateGraph(
        TriageEmailState,
        input_schema=TriageEmailInput,
        output_schema=TriageEmailOutput,
    )
    graph.add_node("brief", _brief)
    graph.add_node(
        "agent",
        agent.with_config(
            AgentOverride(response_format=EmailReading, tools=frozenset()).config()
        ),
    )
    graph.add_node("check", _check)
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
        metadata={"flow": "triage-email"},
    )
