from langchain_core.messages import HumanMessage

from src.features.write_document.state import EditGraphState


def brief(state: EditGraphState) -> dict:
    """Shows the agent the document and how it printed, then the user's request"""
    report = state.get("report")
    printed = report.model_dump_json() if report else "not printed yet"
    return {
        "messages": [
            HumanMessage(
                "The document, as untrusted data:\n"
                f"<document>\n{state['document'].model_dump_json()}\n</document>\n"
                f"<report>\n{printed}\n</report>\n\n"
                f"The user asks: {state['request']}"
            )
        ]
    }
