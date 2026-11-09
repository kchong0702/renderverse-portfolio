import io
import sys
import zipfile
from base64 import b64decode, b64encode
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.app.app import create_app
from src.features.convert_document import service

URL = "/artifact-service/v1/convert"
PDF = b"%PDF-1.7\n%%EOF\n"


def make_docx() -> bytes:
    """A minimal Word file: a zip holding word/document.xml"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
    return buffer.getvalue()


def fake_soffice(tmp_path: Path, pdf: bytes, exit_code: int = 0) -> str:
    """A soffice that outputs pdf and exits with exit_code"""
    (tmp_path / "out.pdf").write_bytes(pdf)
    (tmp_path / "soffice.py").write_text(
        "import shutil, sys\n"
        "args = sys.argv[1:]\n"
        "outdir = args[args.index('--outdir') + 1]\n"
        f"shutil.copy({str(tmp_path / 'out.pdf')!r}, outdir + '/resume.pdf')\n"
        f"sys.exit({exit_code})\n"
    )
    script = tmp_path / "soffice"
    script.write_text(
        f'#!/bin/sh\nexec "{sys.executable}" "{tmp_path}/soffice.py" "$@"\n'
    )
    script.chmod(0o755)
    return str(script)


def use_soffice(monkeypatch: pytest.MonkeyPatch, command: str) -> None:
    """Points the service at command instead of the configured soffice"""
    libreoffice = service._settings.libreoffice.model_copy(update={"command": command})
    monkeypatch.setattr(
        service,
        "_settings",
        service._settings.model_copy(update={"libreoffice": libreoffice}),
    )


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


def test_a_word_file_comes_back_as_a_pdf(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_soffice(monkeypatch, fake_soffice(tmp_path, PDF))

    response = client.post(URL, json={"file": b64encode(make_docx()).decode()})

    assert response.status_code == 200, response.text
    assert b64decode(response.json()["pdf"]) == PDF


def test_a_pdf_comes_back_as_it_is(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_soffice(monkeypatch, "/no/such/soffice")

    response = client.post(URL, json={"file": b64encode(PDF).decode()})

    assert response.status_code == 200, response.text
    assert b64decode(response.json()["pdf"]) == PDF


@pytest.mark.parametrize("exit_code", [1, None])
def test_a_failed_conversion_is_a_422(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int | None,
) -> None:
    use_soffice(
        monkeypatch,
        str(tmp_path / "missing")
        if exit_code is None
        else fake_soffice(tmp_path, b"", exit_code),
    )

    response = client.post(URL, json={"file": b64encode(make_docx()).decode()})

    assert response.status_code == 422
    assert response.json()["detail"] == "the Word file could not be converted to PDF"


def test_a_file_that_is_not_word_is_a_422(client: TestClient) -> None:
    response = client.post(URL, json={"file": b64encode(b"plain text").decode()})

    assert response.status_code == 422
    assert response.json()["detail"] == "upload a PDF or a Word (.docx) file"
