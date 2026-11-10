from src.features.write_document.state import EditGraphState
from src.features.write_document.types import EditOutput


def output(state: EditGraphState) -> EditOutput:
    """The agent's last message as the reply, with the changeset it proposed, if any"""
    return {"reply": state["messages"][-1].text, "changeset": state.get("changeset")}
