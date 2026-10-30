from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml
from jinja2 import Environment, StrictUndefined, meta
from pydantic import BaseModel, Field


class PromptError(ValueError):
    """A prompt's variables do not match what it declares or receives"""


_jinja_env = Environment(
    undefined=StrictUndefined,
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)
"""Missing variables are errors, and `{% %}` lines leave no blank lines behind"""


class Variable(BaseModel):
    name: str
    """Key to be replaced in prompt"""

    description: str
    """Description of the variable"""

    build: Literal["runtime", "compile"]
    """compile: bound once at startup from settings; runtime: rendered before
    every model call from the agent state or the request context"""


class Prompt(BaseModel):
    version: str
    """Version of prompt"""

    description: str
    """Description of what the prompt intended use for"""

    author: str
    """The author of the prompt"""

    date: date
    """The last updated date of the prompt"""

    status: Literal["active", "archieve"]
    """The status of prompt template, archieve is read only and should not be use"""

    input_variables: list[Variable] = Field(default_factory=list)
    """The list of variables to be replaced in prompt"""

    system_prompt: str
    """The actual system prompt to be sent to llm as instruction, a Jinja
    template"""


def load_prompt(path: str | Path) -> Prompt:
    """Load and validate a prompt YAML"""
    with Path(path).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    prompt = Prompt.model_validate(data)

    if prompt.status == "archieve":
        raise RuntimeError(f"Prompt in `{path}` is archieved")

    return prompt


class PromptTemplate:
    """A prompt compiled once with its compile variables bound, rendered with
    its runtime variables on every call"""

    def __init__(self, prompt: Prompt, **compile_values: Any):
        source = prompt.system_prompt
        used = meta.find_undeclared_variables(_jinja_env.parse(source))
        declared = {v.name for v in prompt.input_variables}
        if used != declared:
            raise PromptError(
                f"prompt uses {sorted(used)} but declares {sorted(declared)}"
            )

        compile_names = {v.name for v in prompt.input_variables if v.build == "compile"}
        if set(compile_values) != compile_names:
            raise PromptError(
                f"compile variables {sorted(compile_names)} "
                f"got {sorted(compile_values)}"
            )

        self.runtime_variables = frozenset(declared - compile_names)
        """Names to pass to `render`"""

        self._compile_values = compile_values
        self._template = _jinja_env.from_string(source)

    def render(self, values: Mapping[str, Any] | None = None) -> str:
        """The system prompt for one model call"""
        values = dict(values or {})
        if set(values) != self.runtime_variables:
            raise PromptError(
                f"runtime variables {sorted(self.runtime_variables)} "
                f"got {sorted(values)}"
            )
        return self._template.render({**self._compile_values, **values}).strip()


__all__ = [
    "Prompt",
    "PromptError",
    "PromptTemplate",
    "Variable",
    "load_prompt",
]
