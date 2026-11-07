import json
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from deepagents import DeepAgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import BaseTool
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, ConfigDict, Field, SkipValidation


class AgentConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        arbitrary_types_allowed=True,
        use_attribute_docstrings=True,
    )

    name: str
    """Agent name, such as career-consultant"""

    model: str = Field(pattern=r"^[a-z_-]+:.+$")
    """provider:model, such as anthropic:claude-sonnet-5-5"""

    system_prompt: Path
    """The stage's system.md"""

    skills: Path
    """The stage's skills folder, holding one SKILL.md folder per skill"""

    tools: tuple[BaseTool, ...] = ()
    """Tools the stage adds to the read-only file tools"""

    middleware: tuple[AgentMiddleware, ...] = ()
    """Middleware the stage adds to the deep agent's own"""

    response_format: type[BaseModel]
    """What the agent answers with"""

    state_schema: Annotated[type[DeepAgentState], SkipValidation] = DeepAgentState
    """The agent's state, which the stage's tools read"""

    context_schema: type | None = None
    """What a run passes as context, which the stage's tools read"""

    recursion_limit: int = Field(gt=0)
    """Graph steps a run may take before it fails"""

    @property
    def hash(self) -> str:
        """Sha256 of every setting that changes how the agent behaves"""
        variant = {
            "name": self.name,
            "model": self.model,
            "system_prompt": self.system_prompt.read_text(),
            "skills": {
                str(path.relative_to(self.skills)): path.read_text()
                for path in sorted(self.skills.rglob("*"))
                if path.is_file()
            },
            "tools": [convert_to_openai_tool(tool) for tool in self.tools],
            "middleware": [type(m).__qualname__ for m in self.middleware],
            "response_format": self.response_format.model_json_schema(),
            "recursion_limit": self.recursion_limit,
        }
        return sha256(json.dumps(variant, sort_keys=True).encode()).hexdigest()
