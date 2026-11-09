import json

from langchain.agents.structured_output import StructuredOutputValidationError
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from pydantic_core import to_jsonable_python

from src.agents import AgentOverride
from src.features.import_document.schemas import ResumeImport
from src.features.import_document.state import ImportState


async def structure(state: ImportState, agent: CompiledStateGraph) -> ImportState:
    """Asks agent for the résumé's content, each value citing its lines, with the user's
    note and any failed check's last reply and errors; an unparsed reply is a schema error"""
    try:
        reply = await agent.ainvoke(
            {
                "messages": [
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
            },
            AgentOverride(response_format=ResumeImport).config(),
        )
    except StructuredOutputValidationError as error:
        return {"structured_response": None, "parsing_error": str(error.source)}
    response = reply.get("structured_response")
    return {
        "structured_response": response,
        "parsing_error": None if response else "the reply holds no ResumeImport",
    }
