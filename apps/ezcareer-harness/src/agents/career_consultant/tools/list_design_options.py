import yaml
from document_schema import TemplateSpec
from langchain.tools import ToolRuntime
from langchain_core.tools import tool
from pydantic import TypeAdapter

from src.agents.career_consultant.state import CareerConsultantState
from src.core.config import get_settings


@tool
def list_design_options(runtime: ToolRuntime[None, CareerConsultantState]) -> str:
    """Lists the template specs an update_design edit can use for the document's
    kind; only for changes to how the document looks"""
    specs = [
        TemplateSpec.model_validate(yaml.safe_load(path.read_text()))
        for path in sorted(get_settings().artifact_service.templates.glob("*.yaml"))
    ]
    return (
        TypeAdapter(list[TemplateSpec])
        .dump_json(
            [spec for spec in specs if runtime.state["document"].kind in spec.kinds]
        )
        .decode()
    )
