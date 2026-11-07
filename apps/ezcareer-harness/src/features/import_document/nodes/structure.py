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
    """Asks the LLM for the résumé's content, each value citing its lines"""
    prompt = PromptTemplate.from_template(
        runtime.context.config.prompt, template_format="mustache"
    )
    data = {
        "lines": [{"id": line.id, "text": line.text} for line in state["lines"]],
        "previous_reply": state.get("reply"),
    }
    reply = await runtime.context.model.with_structured_output(
        ResumeImport, include_raw=True
    ).ainvoke(
        [
            SystemMessage(prompt.format(fix_summary=state.get("fix_summary", ""))),
            HumanMessage(json.dumps(data, ensure_ascii=False)),
        ]
    )
    calls = reply["raw"].tool_calls
    return {"reply": calls[0]["args"] if calls else {}}
