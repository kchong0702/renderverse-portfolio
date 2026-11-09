from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.agents.career_consultant.state import CareerConsultantState


@tool
def read_pdf_lines(runtime: ToolRuntime[None, CareerConsultantState]) -> str:
    """Lists the uploaded PDF's lines, one per line, each cited as p<page>.s<n>"""
    return "\n".join(f"{line.id}  {line.text}" for line in runtime.state["lines"])
