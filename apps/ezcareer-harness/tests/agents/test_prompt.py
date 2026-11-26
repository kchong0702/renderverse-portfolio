from pathlib import Path

import pytest

from src.agents.prompt import read_prompt

HEADER = (
    '---\nversion: "1.0"\ndescription: "Greets"\nauthor: "kchong0702"\n'
    'date: "2026-11-25"\nstatus: "{status}"\n---\n\n'
)


def _prompt(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "system.md"
    path.write_text(text)
    return path


def test_a_prompt_is_the_text_after_its_front_matter(tmp_path: Path):
    path = _prompt(tmp_path, HEADER.format(status="active") + "You greet people.\n")

    assert read_prompt(path) == "You greet people."


@pytest.mark.parametrize("version", ["1.10", "2"])
def test_an_unquoted_version_is_refused(tmp_path: Path, version: str):
    text = HEADER.format(status="active").replace('"1.0"', version) + "Hi."

    with pytest.raises(ValueError, match="quote the version"):
        read_prompt(_prompt(tmp_path, text))


def test_a_prompt_with_crlf_line_endings_is_read(tmp_path: Path):
    path = tmp_path / "system.md"
    path.write_bytes(
        (HEADER.format(status="active") + "You greet\npeople.\n")
        .replace("\n", "\r\n")
        .encode()
    )

    assert read_prompt(path) == "You greet\npeople."


def test_front_matter_that_ends_the_file_is_an_empty_prompt(tmp_path: Path):
    text = HEADER.format(status="active").removesuffix("\n\n")

    assert read_prompt(_prompt(tmp_path, text)) == ""


@pytest.mark.parametrize(
    "text",
    [
        "You greet people.",
        "---\nversion: '1.0'\n---\nYou greet people.",
        HEADER.format(status="draft") + "You greet people.",
    ],
)
def test_a_prompt_without_valid_front_matter_is_refused(tmp_path: Path, text: str):
    with pytest.raises(ValueError):
        read_prompt(_prompt(tmp_path, text))


def test_an_archived_prompt_is_refused(tmp_path: Path):
    path = _prompt(tmp_path, HEADER.format(status="archived") + "You greet people.")

    with pytest.raises(ValueError, match="archived"):
        read_prompt(path)
