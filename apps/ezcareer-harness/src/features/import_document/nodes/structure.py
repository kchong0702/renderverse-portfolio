import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic_core import to_jsonable_python

from src.features.import_document.schemas import ResumeImport
from src.features.import_document.state import ImportState


async def structure(
    state: ImportState, model: BaseChatModel, prompt: str
) -> ImportState:
    """Asks the LLM for the résumé's content, each value citing its lines, with the
    user's note and, after a failed check, its last reply and the check's errors"""
    reply = await model.with_structured_output(
        ResumeImport, method="function_calling", include_raw=True
    ).ainvoke(
        [
            SystemMessage(prompt),
            HumanMessage(
                json.dumps(
                    {
                        "lines": [
                            line.model_dump(include={"id", "text"})
                            for line in state["lines"]
                        ],
                        "previous_reply": state.get("structured_response"),
                    },
                    default=to_jsonable_python,
                    ensure_ascii=False,
                )
            ),
            *state.get("messages", []),
        ]
    )
    return {
        "structured_response": reply["parsed"],
        "parsing_error": None
        if reply["parsed"]
        else str(reply["parsing_error"] or "the reply holds no ResumeImport"),
    }
