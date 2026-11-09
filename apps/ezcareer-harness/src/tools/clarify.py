from langchain_core.tools import tool

from src.shared.widget import WidgetSetting, ask


@tool
def clarify(question: str) -> str:
    """Asks the user one short question when the request is unclear, and returns
    their answer. Ask instead of guessing."""
    answer = ask(
        WidgetSetting(
            label=question,
            input_placeholder="Type your answer here...",
            submit_btn="Send",
        )
    )
    return answer.input or "No answer came back. Ask again."
