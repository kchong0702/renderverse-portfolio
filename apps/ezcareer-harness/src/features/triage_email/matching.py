import re

from src.features.triage_email.schemas import Application
from src.shared.email import EmailThread


def _names(text: str, name: str) -> bool:
    """Whether text holds name as whole words, ignoring case"""
    return re.search(rf"\b{re.escape(name.casefold())}\b", text) is not None


def matched_application(
    thread: EmailThread, applications: list[Application]
) -> str | None:
    """Id of the one application whose company the thread names, narrowed by role
    when several do; None when none does or it stays unclear"""
    text = " ".join(
        [thread.subject]
        + [f"{message.sender} {message.text}" for message in thread.messages]
    ).casefold()
    named = [a for a in applications if _names(text, a.company)]
    if len(named) > 1:
        named = [a for a in named if _names(text, a.role)]
    return named[0].id if len(named) == 1 else None
