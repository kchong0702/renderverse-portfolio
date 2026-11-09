import json

from document_schema import Changeset
from langchain_core.messages import ToolMessage

from src.agents import AgentOverride
from src.features.write_document.tools import validate_changeset
from tests.agents.career_consultant.test_career_consultant import (
    GOOD_EDIT,
    _agent,
    _answer,
    _changeset,
    _model,
    _state,
)
from tests.agents.test_builder import _call

BAD_EDIT = GOOD_EDIT.model_copy(
    update={"value": GOOD_EDIT.value.model_copy(update={"src": ["p1.s8"]})}
)


def test_validate_changeset_lists_errors_until_the_changeset_passes():
    model = _model(
        _call(
            "validate_changeset",
            changeset=_changeset(BAD_EDIT).model_dump(mode="json"),
        ),
        _call(
            "validate_changeset",
            changeset=_changeset(GOOD_EDIT).model_dump(mode="json"),
        ),
        _answer(GOOD_EDIT),
    )

    result = _agent(model).invoke(
        _state(),
        AgentOverride(response_format=Changeset, tools=(validate_changeset,)).config(),
    )

    first, second = [
        m.text
        for m in result["messages"]
        if isinstance(m, ToolMessage) and m.name == "validate_changeset"
    ]
    assert [error["rule"] for error in json.loads(first)] == ["unsupported"]
    assert second == "passes"
    assert (
        model.tool_descriptions["validate_changeset"] == validate_changeset.description
    )
