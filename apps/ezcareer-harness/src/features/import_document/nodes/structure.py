import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from src.features.import_document.state import ImportContext, ImportState
from src.shared.models.resume_import import ResumeImport


async def structure(
    state: ImportState, runtime: Runtime[ImportContext]
) -> dict[str, Any]:
    """Asks the LLM for the résumé's content, each value citing its lines, with the
    last reply's errors when it failed"""
    prompt = PromptTemplate.from_template(
        runtime.context.config.prompt, template_format="mustache"
    )
    data: dict[str, Any] = {
        "lines": [{"id": line.id, "text": line.text} for line in state["lines"]]
    }
    if rounds := state.get("rounds"):
        data["previous_reply"] = state["reply"]
        data["errors"] = [error.model_dump() for error in rounds[-1]]
    reply = await runtime.context.model.bind_tools([ResumeImport]).ainvoke(
        [
            SystemMessage(prompt.format()),
            HumanMessage(json.dumps(data, ensure_ascii=False)),
        ]
    )
    return {
        "reply": next(
            (
                call["args"]
                for call in reply.tool_calls
                if call["name"] == "ResumeImport"
            ),
            None,
        )
    }
