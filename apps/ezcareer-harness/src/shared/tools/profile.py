from deepagents import DeepAgentState
from langchain.tools import ToolRuntime
from langchain_core.tools import tool

from src.shared.models import ProfileFact


class ProfileState(DeepAgentState):
    facts: list[ProfileFact]
    """The user's profile facts, which read_profile_facts lists"""


@tool
def read_profile_facts(runtime: ToolRuntime[None, ProfileState]) -> str:
    """Lists the user's profile facts, one per line, each cited as fact:<id>"""
    return "\n".join(f"fact:{fact.id}  {fact.text}" for fact in runtime.state["facts"])
