from pathlib import Path

from document_schema import Changeset

from src.agents import AgentConfig
from src.features.write_document.state import EditState
from src.features.write_document.tools import (
    ask_user,
    design_options,
    read_pdf_lines,
    validate_changeset,
)
from src.shared.tools import read_profile_facts

_HERE = Path(__file__).parent

CAREER_CONSULTANT = AgentConfig(
    name="career-consultant",
    model="anthropic:claude-sonnet-5-5",
    system_prompt=_HERE / "system.md",
    skills=_HERE / "skills",
    tools=(
        read_pdf_lines,
        read_profile_facts,
        design_options(_HERE.parents[4] / "packages/document-renderer/templates"),
        ask_user,
        validate_changeset,
    ),
    response_format=Changeset,
    state_schema=EditState,
    recursion_limit=40,
)
"""The edit stage of career-consultant"""
