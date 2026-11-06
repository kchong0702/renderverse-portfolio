import pytest
from conftest import rich, value
from pydantic import ValidationError

from document_schema import Experience, Link, Projects, Skill


def job(id_: str, bullets: list[str] | None = None) -> dict:
    return {
        "id": id_,
        "role": value("Engineer"),
        "company": value("Acme"),
        "bullets": [{"id": b, "text": rich("Did a thing.")} for b in bullets or []],
    }


def test_entries_in_a_section_need_unique_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Experience(kind="experience", id="exp", items=[job("a"), job("a")])


def test_bullets_in_an_entry_need_unique_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Experience(kind="experience", id="exp", items=[job("a", ["b1", "b1"])])


def test_project_tags_need_unique_ids() -> None:
    tags = [{"id": "t", "text": value("Python")}, {"id": "t", "text": value("Go")}]
    with pytest.raises(ValidationError, match="unique"):
        Projects(
            kind="projects",
            id="pr",
            items=[{"id": "p", "name": value("Ops"), "tags": tags}],
        )


def test_skill_items_need_unique_ids() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Skill(
            id="s",
            items=[
                {"id": "t", "text": value("Python")},
                {"id": "t", "text": value("Go")},
            ],
        )


@pytest.mark.parametrize(
    "url", ["github.com/kelvin", "javascript:alert(1)", "ftp://files"]
)
def test_a_link_must_be_an_http_address(url: str) -> None:
    with pytest.raises(ValidationError):
        Link(id="l", url=value(url))
