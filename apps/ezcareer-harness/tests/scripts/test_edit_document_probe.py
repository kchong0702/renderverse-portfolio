from functools import partial

import httpx

from scripts import probe
from tests.agents.career_consultant.test_career_consultant import (
    BAD_EDIT,
    DONE,
    GOOD_EDIT,
    _model,
    _propose,
)
from tests.features.write_document.test_write_document_graph import (
    _fetched,
    _input,
    _print,
)


async def test_a_probe_runs_the_containers_edit_graph_and_records_each_check_round():
    probe.CONTAINER.reset_singletons()
    probe.CONTAINER.clients.artifact_service(
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(partial(_print, sent=[])),
            base_url="http://artifact-service",
        )
    )
    probe.CONTAINER.career_consultant.agent(
        model=_model(_propose(BAD_EDIT), _propose(GOOD_EDIT), DONE)
    )

    result = await probe.probe(
        probe.WORKFLOWS["edit-document"],
        _input().model_dump(mode="json") | _fetched(),
    )

    assert result["error"] is None
    assert [edit["path"] for edit in result["output"]["changeset"]["edits"]] == [
        GOOD_EDIT.path
    ]
    assert [
        [error["rule"] for error in errors]
        for errors in result["trace"]["check_rounds"]
    ] == [["unsupported"], []]
