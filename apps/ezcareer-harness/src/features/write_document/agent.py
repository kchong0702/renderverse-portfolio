from pathlib import Path

from document_schema import Changeset
from langchain_core.language_models import BaseChatModel
from langgraph.pregel import Pregel

from src.agents import Agent, build_agent
from src.features.write_document.state import EditState
from src.features.write_document.tools import (
    ask_user,
    design_options,
    read_pdf_lines,
    validate_changeset,
)
from src.shared.tools import read_profile_facts

TEMPLATES = Path(__file__).parents[5] / "packages/document-renderer/templates"
"""Folder of the renderer's <id>.yaml template specs"""

TOOLS = (
    read_pdf_lines,
    read_profile_facts,
    design_options(TEMPLATES),
    ask_user,
    validate_changeset,
)
"""What career-consultant can call while it edits a document"""


def career_consultant(agent: Agent, model: BaseChatModel | None = None) -> Pregel:
    """The registered career-consultant agent, built for the edit flow with its
    tools and a Changeset as its answer; model replaces its own"""
    return build_agent(
        agent,
        response_format=Changeset,
        tools=TOOLS,
        state_schema=EditState,
        model=model,
    )
