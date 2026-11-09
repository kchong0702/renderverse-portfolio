import json

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from src.features.import_document.schemas import ResumeImport
from src.features.import_document.state import ImportState


async def structure(
    state: ImportState, model: BaseChatModel, prompt: str
) -> ImportState:
    """Asks the LLM for the résumé's content, each value citing its lines, after
    the user's note if there is one"""
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
                        ]
                    },
                    ensure_ascii=False,
                )
            ),
            *state.get("messages", []),
        ]
    )
    return {"structured_response": reply["parsed"]}
