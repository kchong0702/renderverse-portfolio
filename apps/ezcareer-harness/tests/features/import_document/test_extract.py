import json
from base64 import b64decode, b64encode
from collections.abc import Callable
from functools import partial

import httpx
import pytest

from src.clients.artifact_service import ArtifactServiceClient
from src.features.import_document.exceptions import ImportFailed
from src.features.import_document.nodes import extract
from tests.features.write_document.test_write_document_graph import _fail
from tests.pdfs import make_pdf

WORD = b"PK\x03\x04 a Word file"
WORD_PDF = make_pdf([(10, 10, "Ada Lovelace"), (10, 20, "Engineer")])


def _convert(request: httpx.Request) -> httpx.Response:
    """Converts like artifact-service: a PDF as it is, WORD to WORD_PDF, and a 422
    for any other file"""
    file = b64decode(json.loads(request.content)["file"])
    pdf = WORD_PDF if file == WORD else file
    if not pdf.startswith(b"%PDF"):
        return httpx.Response(
            422, json={"detail": "upload a PDF or a Word (.docx) file"}
        )
    return httpx.Response(200, json={"pdf": b64encode(pdf).decode()})


def _serve(
    request: httpx.Request,
    render: Callable[[httpx.Request], httpx.Response],
    convert: Callable[[httpx.Request], httpx.Response],
) -> httpx.Response:
    """Answers a /v1/convert request with convert and any other with render"""
    return (convert if request.url.path.endswith("/v1/convert") else render)(request)


def _artifact_service(
    render: Callable[[httpx.Request], httpx.Response] = _fail,
    convert: Callable[[httpx.Request], httpx.Response] = _convert,
) -> ArtifactServiceClient:
    """An ArtifactServiceClient on a fake artifact-service that prints with render
    and converts with convert"""
    return ArtifactServiceClient(
        httpx.AsyncClient(
            transport=httpx.MockTransport(
                partial(_serve, render=render, convert=convert)
            ),
            base_url="http://artifact-service",
        )
    )


async def test_a_word_file_is_read_from_the_pdf_artifact_service_converts_it_to():
    result = await extract({"file": WORD}, _artifact_service())

    assert [line.text for line in result["lines"]] == ["Ada Lovelace", "Engineer"]


async def test_a_file_artifact_service_refuses_fails_the_import_with_its_reason():
    with pytest.raises(ImportFailed) as failed:
        await extract({"file": b"plain text"}, _artifact_service())

    assert str(failed.value) == "upload a PDF or a Word (.docx) file"


async def test_an_artifact_service_outage_fails_the_import_until_a_retry():
    with pytest.raises(ImportFailed) as failed:
        await extract({"file": WORD}, _artifact_service(convert=_fail))

    assert str(failed.value) == "couldn't read the file; try again"


async def test_a_pdf_without_text_fails_the_import_with_its_reason():
    with pytest.raises(ImportFailed, match="no text layer"):
        await extract({"file": make_pdf([])}, _artifact_service())
