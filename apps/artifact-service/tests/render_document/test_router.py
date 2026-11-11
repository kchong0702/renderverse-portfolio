import base64
import hashlib
from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.app.app import create_app
from src.features.render_document import service

URL = "/artifact-service/v1/render"
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNg+M8AAAMBAQCv0+FmAAAAAElFTkSuQmCC"
)
PHOTO = hashlib.sha256(PNG).hexdigest()


def value(text: str) -> dict[str, Any]:
    return {"text": text, "src": ["p1.s1"]}


def job(index: int) -> dict[str, Any]:
    return {
        "id": f"j{index}",
        "role": value(f"Engineer {index}"),
        "company": value("Acme"),
        "dates": {"text": value(f"20{10 + index}")},
        "bullets": [
            {"id": f"b{k}", "text": {"html": "Ran payments for millions. " * 3}}
            for k in range(5)
        ],
    }


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def body() -> dict[str, Any]:
    return {
        "document": {
            "kind": "resume",
            "content": {
                "blocks": [
                    {"kind": "profile", "id": "profile", "name": value("Kelvin")},
                    {"kind": "photo", "id": "photo", "file": PHOTO},
                    {"kind": "experience", "id": "exp", "items": [job(0)]},
                ]
            },
            "assets": {PHOTO: {"media_type": "image/png", "uri": "s3://photo"}},
            "design": {"template": "sidebar-band"},
        },
        "assets": {PHOTO: base64.b64encode(PNG).decode()},
    }


def test_render_returns_the_pdf_and_its_report(
    client: TestClient, body: dict[str, Any]
) -> None:
    response = client.post(URL, json=body)

    assert response.status_code == 200, response.text
    pdf = base64.b64decode(response.json()["artifact"])
    report = response.json()["report"]
    assert pdf.startswith(b"%PDF")
    assert report["render_id"] == hashlib.sha256(pdf).hexdigest()
    assert (report["pages"], report["warnings"]) == (1, [])
    assert {span["block"] for span in report["spans"]} == {"profile", "photo", "exp"}


def test_a_long_document_runs_onto_more_pages(
    client: TestClient, body: dict[str, Any]
) -> None:
    body["document"]["content"]["blocks"][2]["items"] = [job(i) for i in range(12)]

    report = client.post(URL, json=body).json()["report"]

    assert report["pages"] >= 2
    assert {"block": "exp", "first_page": 1, "last_page": report["pages"]} in report[
        "spans"
    ]


def test_a_side_column_past_the_first_page_is_reported(
    client: TestClient, body: dict[str, Any]
) -> None:
    body["document"]["design"]["layouts"] = [
        {"template": "sidebar-band", "region": "side", "blocks": ["exp"]}
    ]
    body["document"]["content"]["blocks"][2]["items"] = [job(i) for i in range(12)]

    warnings = client.post(URL, json=body).json()["report"]["warnings"]

    assert [(w["kind"], w["region"]) for w in warnings] == [("region_overflow", "side")]
    assert warnings[0]["by_mm"] > 100


def test_a_render_past_its_timeout_is_a_504(
    client: TestClient, body: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    renderer = service._settings.renderer.model_copy(update={"timeout_s": 0.001})
    monkeypatch.setattr(
        service,
        "_settings",
        service._settings.model_copy(update={"renderer": renderer}),
    )

    response = client.post(URL, json=body)

    assert response.status_code == 504


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"assets": {}}, "assets have no bytes"),
        ({"assets": {PHOTO: base64.b64encode(b"other").decode()}}, "do not hash to"),
    ],
)
def test_asset_bytes_must_match_the_document(
    client: TestClient, body: dict[str, Any], change: dict, message: str
) -> None:
    response = client.post(URL, json={**body, **change})

    assert response.status_code == 422
    assert message in response.text


def test_an_unknown_template_is_rejected(
    client: TestClient, body: dict[str, Any]
) -> None:
    body["document"]["design"]["template"] = "no-such-template"

    response = client.post(URL, json=body)

    assert response.status_code == 422
    assert "no template no-such-template" in response.text


def test_a_template_for_another_kind_is_rejected(client: TestClient) -> None:
    letter = {
        "kind": "cover_letter",
        "content": {
            "blocks": [
                {"kind": "profile", "id": "profile", "name": value("Kelvin")},
                {
                    "kind": "letter",
                    "id": "letter",
                    "greeting": value("Dear Ms Rahman,"),
                    "paragraphs": [
                        {"id": "p1", "text": {"html": "I would like to apply."}}
                    ],
                    "closing": value("Yours sincerely,"),
                },
            ]
        },
        "design": {"template": "classic-two-column"},
    }

    response = client.post(URL, json={"document": letter})

    assert response.status_code == 422
    assert "classic-two-column does not lay out a cover_letter" in response.text
