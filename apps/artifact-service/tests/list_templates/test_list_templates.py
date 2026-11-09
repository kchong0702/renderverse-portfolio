from fastapi.testclient import TestClient

from src.app.app import create_app

URL = "/artifact-service/v1/templates"


def test_templates_lists_every_template() -> None:
    with TestClient(create_app()) as client:
        ids = [spec["id"] for spec in client.get(URL).json()]

    assert "sidebar-band" in ids and "classic-two-column" in ids


def test_templates_for_a_kind_leave_out_the_others() -> None:
    with TestClient(create_app()) as client:
        specs = client.get(URL, params={"kind": "cover_letter"}).json()

    assert specs and all("cover_letter" in spec["kinds"] for spec in specs)
    assert "classic-two-column" not in [spec["id"] for spec in specs]
