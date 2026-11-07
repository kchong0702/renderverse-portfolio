import json
from pathlib import Path

import yaml
from document_schema import Changeset, Design
from langchain.tools import ToolRuntime
from langchain_core.tools import BaseTool, tool
from langgraph.types import interrupt

from src.features.write_document.checks import check_changeset
from src.features.write_document.state import sources


@tool
def read_pdf_lines(runtime: ToolRuntime) -> str:
    """Lists the uploaded PDF's lines, one per line, each cited as p<page>.s<n>"""
    return "\n".join(f"{line.id}  {line.text}" for line in runtime.state["lines"])


@tool
def ask_user(question: str) -> str:
    """Asks the user one question when the request is unclear, and returns the answer"""
    return interrupt(question)


@tool
def validate_changeset(changeset: Changeset, runtime: ToolRuntime) -> str:
    """Checks a changeset before you answer with it, listing what to fix"""
    errors = check_changeset(
        runtime.state["document"], changeset, sources(runtime.state)
    )
    return json.dumps([error.model_dump() for error in errors]) if errors else "passes"


def design_options(templates: Path) -> BaseTool:
    """The list_design_options tool, reading the renderer's template specs from templates"""

    @tool
    def list_design_options(runtime: ToolRuntime) -> str:
        """Lists the templates, fonts and design settings an update_design edit
        can use; only for changes to how the document looks"""
        kind = runtime.state["document"].kind
        specs = [
            yaml.safe_load(path.read_text())
            for path in sorted(templates.glob("*.yaml"))
        ]
        specs = [spec for spec in specs if kind in spec["kinds"]]
        return json.dumps(
            {
                "templates": [
                    {
                        key: spec.get(key)
                        for key in ("id", "name", "description", "accent")
                    }
                    for spec in specs
                ],
                "fonts": sorted(
                    {
                        spec[key]
                        for spec in specs
                        for key in ("body_font", "heading_font")
                    }
                ),
                "design": Design.model_json_schema(),
            }
        )

    return list_design_options
