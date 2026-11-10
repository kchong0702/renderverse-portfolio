from document_schema import DocumentKind
from langchain_core.tools import tool

from src.shared.widget import WidgetSetting, ask


@tool
def choose_document(question: str, kind: DocumentKind | None = None) -> str:
    """Asks the user which of their documents they mean, listing those of kind, and
    returns the title they chose; call find_documents with it next"""
    answer = ask(
        WidgetSetting(label=question, choose="document", kind=kind, submit_btn="Send")
    )
    return answer.input or "No answer came back. Ask again."
