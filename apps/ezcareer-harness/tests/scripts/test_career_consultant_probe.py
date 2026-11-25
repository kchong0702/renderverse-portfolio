from functools import partial

import httpx
from pydantic_core import to_jsonable_python

from scripts import probe
from tests.agents.career_consultant.test_career_consultant import (
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    READ_SKILL,
    _loaded,
    _model,
    _print,
    _propose,
    _state,
)
from tests.agents.test_builder import _call

TASK = {
    "messages": [{"type": "human", "content": "Mention my Kubernetes work"}],
    "document_id": "doc-1",
    **_loaded(),
    "profile_facts": to_jsonable_python(_state()["profile_facts"]),
}


def _container(*replies) -> None:
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    probe.CONTAINER.career_consultant.agent(model=_model(*replies))


async def test_a_probe_runs_the_containers_consultant_and_records_each_check_round():
    _container(READ_SKILL, _propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)

    result = await probe.probe(
        probe.WORKFLOWS["career-consultant"],
        TASK,
    )

    assert result["error"] is None
    assert [edit["path"] for edit in result["output"]["changeset"]["edits"]] == [
        GOOD_EDIT.path
    ]
    assert [
        [error["rule"] for error in errors]
        for errors in result["trace"]["check_rounds"]
    ] == [["unknown_source"], []]


async def test_a_task_without_the_tool_result_fails_with_the_request():
    _container(_call("clarify", question="Which job?"), DONE)

    result = await probe.probe(probe.WORKFLOWS["career-consultant"], TASK)

    assert result["output"] is None
    assert result["error"] == (
        "ValueError: The task has no tool result for {'label': 'Which job?', "
        "'input_placeholder': 'Type your answer here...', 'submit_btn': 'Send'}"
    )
