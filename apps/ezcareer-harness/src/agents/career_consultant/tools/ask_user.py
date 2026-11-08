from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_user(question: str) -> str:
    """Asks the user one question when the request is unclear, and returns the answer"""
    return interrupt(question)
