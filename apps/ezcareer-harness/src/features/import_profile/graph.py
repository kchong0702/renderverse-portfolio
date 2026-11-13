import json
from functools import partial
from typing import Annotated, Literal, TypedDict

from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.managed import RemainingSteps
from langgraph.types import Checkpointer
from pydantic_core import to_jsonable_python

from src.agents import AgentOverride
from src.core.config import get_settings
from src.core.errors import ExecuteError
from src.features.import_profile.checks import check_verbatim
from src.features.import_profile.configurations import ImportProfileConfigurations
from src.features.import_profile.schemas import (
    ExportFile,
    ImportedAbout,
    ImportedEntry,
    ImportedProfile,
    ImportedSkill,
    ImportProfileInput,
)
from src.shared.checks import CheckError, CheckRound, CheckRule, check_round

CHECKS = {"verbatim": check_verbatim}
"""Every check the import-profile configurations.yaml may turn on, by name"""


class ImportProfileState(TypedDict, total=False):
    files: list[ExportFile]
    """The export's profile files"""

    structured_response: ImportedProfile | None
    """The agent's last reply; None when it held no ImportedProfile"""

    parsing_error: str | None
    """Why the last reply held no ImportedProfile; None when it did"""

    errors: list[CheckError]
    """What the latest check found"""

    messages: Annotated[list[AnyMessage], add_messages]
    """The user's note, if any, then each failed check's request to fix its errors"""

    about: ImportedAbout
    """The passing reply's headline, summary, location and links"""

    entries: list[ImportedEntry]
    """The passing reply's roles, education and projects"""

    skills: list[ImportedSkill]
    """The passing reply's skills"""

    remaining_steps: RemainingSteps
    """Graph steps left before the recursion limit"""


async def _structure(
    state: ImportProfileState, agent: CompiledStateGraph
) -> ImportProfileState:
    """Asks agent for the export as profile facts, with the user's note and any
    failed check's last reply and errors"""
    try:
        reply = await agent.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        json.dumps(
                            {
                                "files": state["files"],
                                "previous_reply": state.get("structured_response"),
                            },
                            default=to_jsonable_python,
                            ensure_ascii=False,
                        )
                    ),
                    *state.get("messages", []),
                ]
            },
            AgentOverride(response_format=ImportedProfile).config(),
        )
    except StructuredOutputValidationError as error:
        return {"structured_response": None, "parsing_error": str(error.source)}
    response = reply.get("structured_response")
    return {
        "structured_response": response,
        "parsing_error": None if response else "the reply holds no ImportedProfile",
    }


def _verify(
    state: ImportProfileState, configurations: ImportProfileConfigurations
) -> CheckRound | ImportProfileState:
    """Checks the last reply against the export's rows and keeps it once it passes"""
    if (reply := state["structured_response"]) is None:
        return check_round(
            [CheckError(rule=CheckRule.SCHEMA, at="", message=state["parsing_error"])]
        )
    if errors := [
        error
        for name in configurations.checks
        for error in CHECKS[name](reply, state["files"])
    ]:
        return check_round(errors)
    return {
        **check_round([]),
        "about": reply.about,
        "entries": reply.entries,
        "skills": reply.skills,
    }


def _after_verify(state: ImportProfileState) -> Literal["structure", "__end__"]:
    """Ends on a reply that passed the checks; sends one that failed back to
    structure while steps remain for structure and verify"""
    if not state["errors"]:
        return END
    if state["remaining_steps"] < 2:
        raise ExecuteError(
            "the export didn't pass its checks: "
            + "; ".join(f"{e.at} ({e.rule}): {e.message}" for e in state["errors"])
        )
    return "structure"


def build_graph(
    agent: CompiledStateGraph, checkpointer: Checkpointer = None
) -> CompiledStateGraph:
    """The import-profile graph run on agent, with the configurations the settings
    name; checkpointer keeps runs"""
    configurations = (
        get_settings().graph_profile("import-profile").load(ImportProfileConfigurations)
    )
    graph = StateGraph(
        ImportProfileState,
        input_schema=ImportProfileInput,
        output_schema=ImportedProfile,
    )
    graph.add_node("structure", partial(_structure, agent=agent))
    graph.add_node("verify", partial(_verify, configurations=configurations))
    graph.add_edge(START, "structure")
    graph.add_edge("structure", "verify")
    graph.add_conditional_edges("verify", _after_verify)
    return graph.compile(checkpointer=checkpointer).with_config(
        recursion_limit=configurations.recursion_limit,
        metadata={"flow": "import-profile"},
    )
