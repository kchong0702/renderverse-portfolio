from collections.abc import Callable, Sequence
from functools import partial
from typing import Annotated, Self
from zoneinfo import ZoneInfo

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Checkpointer
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.agents import AgentOverride
from src.core.config import get_settings
from src.features.draft_reply.configurations import CHECKS, DraftReplyConfigurations
from src.features.draft_reply.schemas import Application, DraftReply
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round
from src.shared.email import EmailThread, TimeSlot, untrusted_thread
from src.shared.profile import ProfileFact


class DraftReplyInput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    thread: EmailThread | None = None
    """The email thread to answer; None writes a follow-up for the application"""

    application: Application | None = None
    """The application to follow up on when there is no thread"""

    free_slots: list[TimeSlot] = Field(default_factory=list)
    """Times the user is free, which the email may offer"""

    timezone: ZoneInfo
    """The user's time zone, such as Europe/London"""

    facts: list[ProfileFact] = Field(default_factory=list)
    """The user's profile facts"""

    messages: Annotated[list[AnyMessage], add_messages] = Field(default_factory=list)
    """The user's note, if any, then the agent's conversation across check rounds"""

    @model_validator(mode="after")
    def _has_something_to_answer(self) -> Self:
        """Rejects a request with neither a thread nor an application"""
        if self.thread is None and self.application is None:
            raise ValueError("Send a thread to answer or an application to follow up")
        return self


class DraftReplyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    body: str = ""
    """The plain-text email; empty only before the run ends"""

    slots: list[TimeSlot] = Field(default_factory=list)
    """The free slots the email offers; empty when it offers no times"""


class DraftReplyState(DraftReplyInput, DraftReplyOutput):
    model_config = ConfigDict(extra="forbid", use_attribute_docstrings=True)

    structured_response: DraftReply | None = None
    """The agent's latest answer"""

    errors: list[CheckError] = Field(default_factory=list)
    """What the latest check found"""


def _brief(state: DraftReplyState, max_free_slots: int) -> dict:
    """Ask the agent for the reply or the follow-up, listing the earliest
    max_free_slots free slots by id in the user's time zone"""
    free_slots = sorted(state.free_slots, key=lambda slot: slot.start)[:max_free_slots]
    if state.thread:
        task = (
            f"Draft my reply to this email thread.\n\n{untrusted_thread(state.thread)}"
        )
    else:
        application = state.application
        applied = (
            f" on {application.applied_at.isoformat()}"
            if application.applied_at
            else ""
        )
        task = (
            f"Draft a follow-up email for my application for {application.role} at"
            f" {application.company}, sent{applied}. It is at the {application.stage}"
            " stage and nobody has replied."
        )
    slots = "\n".join(
        f"[{number}] {slot.start.astimezone(state.timezone):%a %d %b %H:%M}"
        f" to {slot.end.astimezone(state.timezone):%H:%M}"
        for number, slot in enumerate(free_slots, start=1)
    )
    return {
        "free_slots": free_slots,
        "messages": [
            HumanMessage(
                f"{task}\n\nMy free slots, in {state.timezone.key}:\n{slots}"
                if slots
                else f"{task}\n\nI have no free slots to offer."
            )
        ],
    }


def _check(
    state: DraftReplyState,
    checks: Sequence[Callable[[DraftReply, list[TimeSlot]], list[CheckError]]],
) -> CheckRound:
    """Run the configured checks on the agent's answer, or ask for one"""
    if state.structured_response is None:
        return check_round(
            [
                CheckError(
                    rule=CheckRule.NO_ANSWER,
                    at="answer",
                    message="Reply with a DraftReply",
                )
            ]
        )
    return check_round(
        [
            error
            for check in checks
            for error in check(state.structured_response, state.free_slots)
        ]
    )


def _output(state: DraftReplyState) -> dict:
    """The email with the free slots it offers, in the order it lists them"""
    return {
        "body": state.structured_response.body,
        "slots": [
            state.free_slots[slot_id - 1]
            for slot_id in dict.fromkeys(state.structured_response.slot_ids)
        ],
    }


def build_graph(
    agent: CompiledStateGraph, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The draft-reply workflow run on agent, with the configurations the settings
    name; checkpointer keeps its runs"""
    configurations = (
        get_settings().graph_profile("draft-reply").load(DraftReplyConfigurations)
    )
    graph = StateGraph(
        DraftReplyState, input_schema=DraftReplyInput, output_schema=DraftReplyOutput
    )
    graph.add_node(
        "brief", partial(_brief, max_free_slots=configurations.max_free_slots)
    )
    graph.add_node(
        "agent",
        agent.with_config(
            AgentOverride(
                response_format=DraftReply,
                tools=frozenset({"read_profile_facts"}),
            ).config()
        ),
    )
    graph.add_node(
        "check",
        partial(_check, checks=[CHECKS[name] for name in configurations.checks]),
    )
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
        metadata={"flow": "draft-reply"},
    )
