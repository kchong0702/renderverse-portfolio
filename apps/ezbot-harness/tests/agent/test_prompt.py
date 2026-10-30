import pytest
from pydantic import ValidationError

from src.features.agent.prompt import PromptError, PromptTemplate, load_prompt

HEADER = """\
version: "1.0"
description: "Test prompt"
author: "tester"
date: "2026-10-25"
"""

VARIABLES = """\
input_variables:
  - name: tone
    description: "compile"
    build: "compile"
  - name: mood
    description: "runtime"
    build: "runtime"
"""

CONDITIONAL = """\
system_prompt: |
  Be {{ tone }}.
  {% if mood == "busy" %}
  Keep it short.
  {% else %}
  Take your time.
  {% endif %}
"""


def write(tmp_path, body: str):
    path = tmp_path / "prompt.yaml"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def template(tmp_path, body: str = VARIABLES + CONDITIONAL, **compile_values):
    prompt = load_prompt(write(tmp_path, 'status: "active"\n' + body))
    return PromptTemplate(prompt, **compile_values)


def test_runtime_variables_drive_conditions(tmp_path):
    prompt = template(tmp_path, tone="kind")

    assert prompt.runtime_variables == {"mood"}
    assert prompt.render({"mood": "busy"}) == "Be kind.\nKeep it short."
    assert prompt.render({"mood": "calm"}) == "Be kind.\nTake your time."


def test_prompt_must_declare_exactly_the_variables_it_uses(tmp_path):
    undeclared = 'system_prompt: "Hi {{ name }}"\n'
    unused = VARIABLES + 'system_prompt: "Hi"\n'

    with pytest.raises(PromptError, match="declares"):
        template(tmp_path, undeclared)
    with pytest.raises(PromptError, match="declares"):
        template(tmp_path, unused, tone="kind")


def test_compile_variables_are_all_required_at_load(tmp_path):
    with pytest.raises(PromptError, match="compile variables"):
        template(tmp_path)
    with pytest.raises(PromptError, match="compile variables"):
        template(tmp_path, tone="kind", extra=1)


def test_runtime_variables_are_all_required_at_render(tmp_path):
    prompt = template(tmp_path, tone="kind")

    with pytest.raises(PromptError, match="runtime variables"):
        prompt.render({})


def test_archived_prompt_is_refused(tmp_path):
    with pytest.raises(RuntimeError, match="archieved"):
        load_prompt(write(tmp_path, 'status: "archieve"\nsystem_prompt: "old"\n'))


def test_prompt_without_system_prompt_is_rejected(tmp_path):
    with pytest.raises(ValidationError, match="system_prompt"):
        load_prompt(write(tmp_path, 'status: "active"\n'))
