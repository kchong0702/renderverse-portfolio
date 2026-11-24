from pathlib import Path
from string import Template

import pytest

from src.agents import middlewares
from src.agents.middlewares import ParentHandoffMiddleware
from src.agents.prompt import read_prompt
from src.core.config import get_settings

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


def test_parent_handoff_middleware_reads_its_prompt_from_the_middleware_prompts_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "parent_handoff.md").write_text(
        HEADER.format(status="active") + "Hand it back.\n"
    )
    settings = get_settings().model_copy(update={"middleware_prompts": tmp_path})
    monkeypatch.setattr(middlewares.parent_handoff, "get_settings", lambda: settings)

    assert ParentHandoffMiddleware().hand_back == "Hand it back."


@pytest.mark.parametrize(
    "path",
    sorted(get_settings().middleware_prompts.glob("*.md")),
    ids=lambda path: path.name,
)
def test_each_middleware_prompt_loads_and_fills(path: Path):
    template = Template(read_prompt(path))

    template.substitute({name: "x" for name in template.get_identifiers()})
