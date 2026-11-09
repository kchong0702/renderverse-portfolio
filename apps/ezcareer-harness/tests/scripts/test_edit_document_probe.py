from functools import partial

import httpx

from scripts import probe
from tests.agents.career_consultant.test_career_consultant import (
    GOOD_EDIT,
    _answer,
    _model,
)
from tests.features.write_document.test_validate_changeset import BAD_EDIT
from tests.features.write_document.test_write_document_graph import _input, _print


async def test_a_probe_runs_the_containers_edit_graph_and_records_each_check_round():
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    probe.CONTAINER.career_consultant.agent(
        model=_model(_answer(BAD_EDIT), _answer(GOOD_EDIT))
    )

    result = await probe.probe(
        probe.WORKFLOWS["edit-document"], _input().model_dump(mode="json")
    )

    assert result["error"] is None
    assert [edit["path"] for edit in result["output"]["changeset"]["edits"]] == [
        GOOD_EDIT.path
    ]
    assert [
        [error["rule"] for error in errors]
        for errors in result["trace"]["check_rounds"]
    ] == [["unsupported"], []]
