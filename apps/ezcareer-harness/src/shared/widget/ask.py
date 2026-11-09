from langgraph.config import get_config
from langgraph.types import interrupt

from src.shared.widget.types import Answer, WidgetSetting


def ask(widget: WidgetSetting) -> Answer:
    """Pauses the run until answered: a parent agent, when the run has one, gets the
    widget's label as plain text; otherwise the user gets the widget"""
    value = interrupt(
        widget.label
        if get_config()["configurable"].get("parent")
        else widget.model_dump(exclude_none=True)
    )
    return (
        Answer(input=value) if isinstance(value, str) else Answer.model_validate(value)
    )
