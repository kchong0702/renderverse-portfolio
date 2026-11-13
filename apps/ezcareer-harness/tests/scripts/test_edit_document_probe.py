from functools import partial

import httpx

from scripts import probe
from tests.agents.career_consultant.test_career_consultant import (
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    READ_SKILL,
    _model,
    _propose,
)
from tests.features.write_document.test_write_document_graph import (
    _input,
    _loaded,
    _print,
)


def _container(*replies) -> None:
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    probe.CONTAINER.career_consultant.agent(model=_model(*replies))


async def test_a_probe_runs_the_containers_edit_graph_and_records_each_check_round():
    _container(READ_SKILL, _propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)

    result = await probe.probe(
        probe.WORKFLOWS["edit-document"],
        _input().model_dump(mode="json") | {"tool_results": {"document": _loaded()}},
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
    _container(DONE)

    result = await probe.probe(
        probe.WORKFLOWS["edit-document"], _input().model_dump(mode="json")
    )

    assert result["output"] is None
    assert result["error"] == (
        "ValueError: The task has no tool result for "
        f"{{'execute_tool': 'document', 'id': '{_input().document_id}'}}"
    )
