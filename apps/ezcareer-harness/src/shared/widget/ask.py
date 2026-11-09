from langgraph.config import get_config
from langgraph.types import interrupt

from src.shared.widget.types import Answer, ParentRequest, WidgetSetting


def ask(parent_request: ParentRequest, widget: WidgetSetting) -> Answer:
    """Pauses the run and sends only one of the two: parent_request to the parent
    agent when there is one, who picks its own widget, otherwise widget to the user"""
    value = interrupt(
        (
            parent_request if get_config()["configurable"].get("parent") else widget
        ).model_dump(exclude_none=True)
    )
    return (
        Answer(input=value) if isinstance(value, str) else Answer.model_validate(value)
    )
