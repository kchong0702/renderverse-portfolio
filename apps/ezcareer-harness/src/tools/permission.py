from langchain_core.tools import tool

from src.shared.widget import ParentRequest, WidgetSetting, ask


@tool
def permission(summary: str) -> str:
    """Asks the user to confirm an action before you take it; summary says in one
    sentence what the action does, side effects included"""
    answer = ask(
        ParentRequest(kind="permission", text=summary),
        WidgetSetting(label=summary, submit_btn="Confirm", cancel_btn="Cancel"),
    )
    if answer.accept is None:
        return "No answer came back. Ask again."
    return (
        f"Permission granted: {summary}. Go ahead."
        if answer.accept
        else f"Permission refused: {summary}. Don't do it."
    )
