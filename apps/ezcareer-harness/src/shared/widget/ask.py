from langgraph.config import get_config
from langgraph.types import interrupt

from src.shared.widget.types import Answer, ParentQuestion, WidgetSetting


def ask(question: ParentQuestion, widget: WidgetSetting) -> Answer:
    """Pauses the run until answered: a parent agent, when the run has one, gets
    question; otherwise the user gets widget"""
    return Answer.model_validate(
        interrupt(
            (
                question if get_config()["configurable"].get("parent") else widget
            ).model_dump(exclude_none=True)
        )
    )
