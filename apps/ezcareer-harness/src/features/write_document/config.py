from pathlib import Path

from document_schema import Changeset

from src.agents import AgentConfig, Stage
from src.features.write_document.checks import check_changeset
from src.features.write_document.state import EditState
from src.features.write_document.tools import (
    ask_user,
    design_options,
    read_pdf_lines,
    validate_changeset,
)
from src.shared.tools import read_profile_facts

_HERE = Path(__file__).parent

TEMPLATES = _HERE.parents[4] / "packages/document-renderer/templates"
"""Folder of the renderer's <id>.yaml template specs"""

HARNESS = _HERE / "harness"
"""The career-consultant harness the app runs"""

STAGE = Stage(
    tools={
        tool.name: tool
        for tool in (
            read_pdf_lines,
            read_profile_facts,
            design_options(TEMPLATES),
            ask_user,
            validate_changeset,
        )
    },
    response_formats={"Changeset": Changeset},
    checks={"changeset": check_changeset},
    state_schema=EditState,
)
"""What a career-consultant harness may pick from in the edit stage"""

CAREER_CONSULTANT = AgentConfig.load(HARNESS, STAGE)
"""The edit stage of career-consultant, loaded from its harness folder"""
