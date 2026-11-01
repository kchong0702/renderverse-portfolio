import base64
from collections.abc import Iterator
from typing import Any

import pytest
from conftest import PNG, PNG_SHA
from fastapi.testclient import TestClient

from src.app.app import create_app

URL = "/artifact-service/v1/render"


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def _body(document: dict[str, Any], assets_data: dict[str, bytes]) -> dict[str, Any]:
    return {
        "document": document,
        "assets_data": {
            sha: base64.b64encode(data).decode() for sha, data in assets_data.items()
        },
    }


def test_render_returns_html_pdf_and_report(
    client: TestClient, document_data: dict[str, Any]
) -> None:
    response = client.post(URL, json=_body(document_data, {PNG_SHA: PNG}))

    assert response.status_code == 200
    body = response.json()
    assert base64.b64decode(body["pdf"]).startswith(b"%PDF")
    assert "data:image/png;base64," in body["html"]
    assert body["report"]["pages"] == 1
    assert body["report"]["unbound_fields"] == []


def test_asset_bytes_must_hash_to_their_key(
    client: TestClient, document_data: dict[str, Any]
) -> None:
    response = client.post(URL, json=_body(document_data, {PNG_SHA: b"other"}))

    assert response.status_code == 422
    assert "do not hash to" in response.text


def test_every_document_asset_needs_its_bytes(
    client: TestClient, document_data: dict[str, Any]
) -> None:
    response = client.post(URL, json=_body(document_data, {}))

    assert response.status_code == 422
    assert "has no bytes" in response.text


def test_a_template_the_renderer_refuses_is_a_422(
    client: TestClient, document_data: dict[str, Any]
) -> None:
    document_data["template"]["html"] += "{{{header.name.text}}}"

    response = client.post(URL, json=_body(document_data, {PNG_SHA: PNG}))

    assert response.status_code == 422
    assert "unescaped output" in response.json()["detail"]
