import io
import zipfile

import pytest

from src.features.profile.exceptions import UnreadableExport
from src.features.profile.export import read_export
from tests.conftest import PREFIX, _client, a2a_sent, a2a_task
from tests.core.conftest import DATABASE_URL

PROFILE = f"{PREFIX}/profile"

MISSING_ID = "00000000-0000-0000-0000-000000000000"

POSITIONS = (
    "Company Name,Title,Description,Location,Started On,Finished On\n"
    "Acme Corp,Senior Engineer,Led the platform team,Kuala Lumpur,Mar 2022,\n"
)

ACME = {
    "kind": "role",
    "title": "Senior Engineer",
    "organisation": "Acme Corp",
    "location": "Kuala Lumpur",
    "start": "2022-03",
    "end": "present",
    "summary": "Led the platform team",
    "highlights": [],
    "link": None,
    "code_link": None,
    "tools": [],
}

RENDERVERSE = {
    "kind": "project",
    "title": "Renderverse",
    "organisation": "",
    "location": "",
    "start": None,
    "end": None,
    "summary": "3D portfolio you can walk through",
    "highlights": [],
    "link": "https://kelvinchong.dev",
    "code_link": None,
    "tools": ["React", "Three.js"],
}


def _export(*extra: str, **files: str) -> bytes:
    """A profile export zip holding these CSV files under a folder; extra makes
    otherwise equal exports differ"""
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name, content in files.items():
            archive.writestr(f"Basic_Export/{name.replace('_', ' ')}.csv", content)
        for number, note in enumerate(extra):
            archive.writestr(f"Basic_Export/Notes {number}.txt", note)
    return data.getvalue()


def _profile(
    *entries: dict, about: dict | None = None, skills: list | None = None
) -> dict:
    """import-profile's reply"""
    reply = {
        "about": {"headline": "", "summary": "", "location": "", "links": []}
        | (about or {}),
        "entries": list(entries),
        "skills": skills or [],
    }
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply}])


async def _import(client, harness, outcome, data: bytes, name="export.zip"):
    """Upload a file to the profile with the harness answering outcome"""
    harness.outcomes.append(outcome)
    media = "application/zip" if name.endswith(".zip") else "application/pdf"
    return await client.post(f"{PROFILE}/imports", files={"file": (name, data, media)})


async def _changes(client) -> list[dict]:
    return (await client.get(f"{PROFILE}/changes")).json()


async def test_an_export_adds_what_the_profile_lacks(client, harness):
    me = (await client.get(f"{PREFIX}/me")).json()
    data = _export(
        Profile="First Name,Last Name,Headline\nKelvin,Chong,Backend engineer\n",
        Positions=POSITIONS,
        Email_Addresses=(
            "Email Address,Confirmed,Primary\n"
            "old@example.com,Yes,No\n"
            "kelvin@example.com,Yes,Yes\n"
        ),
        PhoneNumbers="Extension,Number,Type\n,+60 12-345 6789,Mobile\n",
        Messages="FROM,TO,CONTENT\nsomeone,me,hello\n",
    )
    about = {
        "headline": "Backend engineer",
        "location": "Kuala Lumpur",
        "links": [{"label": "GitHub", "url": "https://github.com/kchong0702"}],
    }
    skills = [{"name": "Python", "group": "Languages"}]

    imported = await _import(
        client, harness, _profile(ACME, RENDERVERSE, about=about, skills=skills), data
    )

    assert imported.status_code == 201
    assert imported.json() | {"id": None, "created_at": None} == {
        "id": None,
        "filename": "export.zip",
        "media_type": "application/zip",
        "source": "data",
        "added": 9,
        "conflicts": 0,
        "matched": 0,
        "created_at": None,
    }
    profile = (await client.get(PROFILE)).json()
    assert profile["name"] == "Kelvin Chong"
    assert profile["email"] == "kelvin@example.com"
    assert profile["phone"] == "+60 12-345 6789"
    assert profile["headline"] == "Backend engineer"
    assert profile["links"] == about["links"]
    entries = (await client.get(f"{PROFILE}/entries")).json()
    assert {(e["title"], e["archived"], e["on_site"]) for e in entries} == {
        ("Senior Engineer", False, False),
        ("Renderverse", False, False),
    }
    assert [s["name"] for s in (await client.get(f"{PROFILE}/skills")).json()] == [
        "Python"
    ]
    assert await _changes(client) == []
    [request] = harness.received
    assert request.url.path == "/ezcareer/a2a/import-profile"
    message = a2a_sent(harness)[0]["params"]["message"]
    assert message["contextId"].startswith(f"{me['id']}:")
    files = message["parts"][0]["data"]["files"]
    assert [f["name"] for f in files] == ["Profile.csv", "Positions.csv"]
    assert files[1]["rows"] == [
        {
            "Company Name": "Acme Corp",
            "Title": "Senior Engineer",
            "Description": "Led the platform team",
            "Location": "Kuala Lumpur",
            "Started On": "Mar 2022",
            "Finished On": "",
        }
    ]
    listed = (await client.get(f"{PROFILE}/imports")).json()
    assert [i["id"] for i in listed] == [imported.json()["id"]]


async def test_the_same_file_again_changes_nothing(client, harness):
    data = _export(Positions=POSITIONS)
    first = await _import(client, harness, _profile(ACME), data)

    again = await _import(client, harness, _profile(ACME), data)

    assert again.status_code == 201
    assert again.json()["id"] == first.json()["id"]
    assert len(harness.received) == 1
    assert len((await client.get(f"{PROFILE}/entries")).json()) == 1
    assert len((await client.get(f"{PROFILE}/imports")).json()) == 1


async def test_new_items_are_added_once(client, harness):
    skills = [{"name": "Python", "group": "Languages"}]
    await _import(
        client, harness, _profile(ACME, skills=skills), _export(Positions=POSITIONS)
    )

    again = await _import(
        client,
        harness,
        _profile(ACME | {"title": "SENIOR ENGINEER"}, skills=[{"name": "python"}]),
        _export("later", Positions=POSITIONS),
    )

    assert (again.json()["added"], again.json()["matched"]) == (0, 2)
    assert len((await client.get(f"{PROFILE}/entries")).json()) == 1
    assert len((await client.get(f"{PROFILE}/skills")).json()) == 1
    assert await _changes(client) == []


async def test_differing_values_wait_as_one_conflict_per_field(client, harness):
    await client.patch(PROFILE, json={"headline": "Backend engineer"})
    entry = (await client.post(f"{PROFILE}/entries", json=ACME)).json()
    first = await _import(
        client,
        harness,
        _profile(
            ACME | {"summary": "Ran the platform team", "location": ""},
            about={"headline": "Platform engineer"},
        ),
        _export("first", Positions=POSITIONS),
    )
    assert (first.json()["conflicts"], first.json()["matched"]) == (2, 1)

    newer = await _import(
        client,
        harness,
        _profile(
            ACME | {"summary": "Grew the platform team"},
            about={"headline": "Staff engineer"},
        ),
        _export("newer", Positions=POSITIONS),
    )

    changes = await _changes(client)
    assert [
        (c["entry_id"], c["field"], c["current"], c["conflict"]) for c in changes
    ] == [
        (None, "headline", "Backend engineer", "Staff engineer"),
        (entry["id"], "summary", "Led the platform team", "Grew the platform team"),
    ]
    assert {c["import_id"] for c in changes} == {newer.json()["id"]}
    assert {c["kind"] for c in changes} == {"field"}
    assert (await client.get(PROFILE)).json()["headline"] == "Backend engineer"

    await _import(
        client,
        harness,
        _profile(ACME, about={"headline": "backend engineer."}),
        _export("agrees", Positions=POSITIONS),
    )

    assert await _changes(client) == []


async def test_a_year_only_date_agrees_with_any_month_of_it(client, harness):
    await client.post(f"{PROFILE}/entries", json=ACME)

    imported = await _import(
        client,
        harness,
        _profile(ACME | {"start": "2022"}),
        _export(Positions=POSITIONS),
    )

    assert (imported.json()["matched"], imported.json()["conflicts"]) == (1, 0)


async def test_a_close_match_waits_and_a_newer_import_updates_it(client, harness):
    globex = ACME | {"organisation": "Globex Inc.", "summary": "Kept the lights on"}
    entry = (await client.post(f"{PROFILE}/entries", json=globex)).json()
    await _import(
        client,
        harness,
        _profile(globex | {"organisation": "Globex"}),
        _export("first", Positions=POSITIONS),
    )

    newer = await _import(
        client,
        harness,
        _profile(globex | {"organisation": "Globex", "summary": "Ran the platform"}),
        _export("newer", Positions=POSITIONS),
    )

    assert newer.json()["conflicts"] == 1
    [change] = await _changes(client)
    assert change["kind"] == "match"
    assert change["entry_id"] == entry["id"]
    assert change["import_id"] == newer.json()["id"]
    assert change["entry"]["organisation"] == "Globex"
    assert change["entry"]["summary"] == "Ran the platform"
    assert len((await client.get(f"{PROFILE}/entries")).json()) == 1


async def test_a_close_match_needs_no_organisation(client, harness):
    entry = (await client.post(f"{PROFILE}/entries", json=RENDERVERSE)).json()

    await _import(
        client,
        harness,
        _profile(RENDERVERSE | {"title": "Renderverse portfolio"}),
        _export(Positions=POSITIONS),
    )

    [change] = await _changes(client)
    assert (change["kind"], change["entry_id"]) == ("match", entry["id"])
    assert len((await client.get(f"{PROFILE}/entries")).json()) == 1


async def test_resolving_a_field_keeps_or_takes_the_imported_value(client, harness):
    await client.patch(PROFILE, json={"headline": "Backend engineer"})
    entry = (await client.post(f"{PROFILE}/entries", json=ACME)).json()
    await _import(
        client,
        harness,
        _profile(
            ACME | {"highlights": ["Cut deploys to 5 minutes."]} | {"end": "2025-01"},
            about={"headline": "Platform engineer"},
        ),
        _export(Positions=POSITIONS),
    )
    changes = {c["field"]: c["id"] for c in await _changes(client)}

    remaining = await client.post(
        f"{PROFILE}/changes/resolve",
        json={
            "answers": [
                {"id": changes["headline"], "choice": "current"},
                {"id": changes["end"], "choice": "conflict"},
            ]
        },
    )

    assert remaining.status_code == 200
    assert remaining.json() == []
    assert (await client.get(PROFILE)).json()["headline"] == "Backend engineer"
    [stored] = (await client.get(f"{PROFILE}/entries")).json()
    assert stored["id"] == entry["id"]
    assert stored["end"] == "2025-01"
    assert stored["highlights"] == ["Cut deploys to 5 minutes."]


async def test_resolving_a_match_merges_it_or_adds_it(client, harness):
    globex = ACME | {"organisation": "Globex Inc."}
    other = ACME | {"organisation": "Initech Inc.", "title": "Engineer"}
    first = (await client.post(f"{PROFILE}/entries", json=globex)).json()
    await client.post(f"{PROFILE}/entries", json=other)
    await _import(
        client,
        harness,
        _profile(
            globex | {"organisation": "Globex"}, other | {"organisation": "Initech"}
        ),
        _export(Positions=POSITIONS),
    )
    matches = {c["entry"]["organisation"]: c["id"] for c in await _changes(client)}

    remaining = await client.post(
        f"{PROFILE}/changes/resolve",
        json={
            "answers": [
                {"id": matches["Globex"], "choice": "same"},
                {"id": matches["Initech"], "choice": "different"},
            ]
        },
    )

    assert [
        (c["kind"], c["entry_id"], c["field"], c["current"], c["conflict"])
        for c in remaining.json()
    ] == [("field", first["id"], "organisation", "Globex Inc.", "Globex")]
    entries = (await client.get(f"{PROFILE}/entries")).json()
    assert sorted(e["organisation"] for e in entries) == [
        "Globex Inc.",
        "Initech",
        "Initech Inc.",
    ]


async def test_an_answer_must_fit_its_change(client, harness):
    await client.post(f"{PROFILE}/entries", json=ACME | {"organisation": "Globex Inc."})
    await _import(
        client,
        harness,
        _profile(ACME | {"organisation": "Globex"}),
        _export(Positions=POSITIONS),
    )
    [change] = await _changes(client)

    wrong = await client.post(
        f"{PROFILE}/changes/resolve",
        json={"answers": [{"id": change["id"], "choice": "conflict"}]},
    )
    missing = await client.post(
        f"{PROFILE}/changes/resolve",
        json={"answers": [{"id": MISSING_ID, "choice": "current"}]},
    )

    assert wrong.status_code == 422
    assert missing.status_code == 404
    assert len(await _changes(client)) == 1


RESUME = {
    "kind": "resume",
    "content": {
        "blocks": [
            {
                "kind": "profile",
                "id": "profile",
                "name": {"text": "Kelvin Chong"},
                "headline": {"text": "Backend engineer"},
            },
            {
                "kind": "contacts",
                "id": "contacts",
                "items": [
                    {"id": "e", "kind": "email", "value": {"text": "k@example.com"}},
                    {
                        "id": "l",
                        "kind": "linkedin",
                        "value": {"text": "linkedin.com/in/kelvin"},
                    },
                ],
            },
            {
                "kind": "experience",
                "id": "experience",
                "items": [
                    {
                        "id": "acme",
                        "role": {"text": "Senior Engineer"},
                        "company": {"text": "Acme Corp"},
                        "dates": {
                            "text": {"text": "2022 to now"},
                            "start": "2022",
                            "end": "present",
                        },
                        "bullets": [
                            {
                                "id": "b1",
                                "text": {"html": "Cut <b>deploys</b> to 5 min."},
                            }
                        ],
                    }
                ],
            },
            {
                "kind": "projects",
                "id": "projects",
                "items": [
                    {
                        "id": "rv",
                        "name": {"text": "Renderverse"},
                        "links": [
                            {"id": "c", "url": {"text": "https://github.com/k/rv"}},
                            {"id": "s", "url": {"text": "https://kelvinchong.dev"}},
                        ],
                        "tags": [{"id": "r", "text": {"text": "React"}}],
                    }
                ],
            },
            {
                "kind": "skills",
                "id": "skills",
                "items": [
                    {
                        "id": "lang",
                        "label": {"text": "Languages"},
                        "items": [{"id": "py", "text": {"text": "Python"}}],
                    }
                ],
            },
            {
                "kind": "languages",
                "id": "spoken",
                "items": [{"id": "ms", "language": {"text": "Malay"}}],
            },
        ]
    },
}


def resume_reply(document: dict = RESUME) -> dict:
    """import-resume's reply for an uploaded résumé"""
    reply = {
        "document": document,
        "pdf": "JVBERi0=",
        "report": {"render_id": "0" * 64, "pages": 1, "last_page_fill": 0.4},
        "lines": [],
        "suggestion": {"template": "serif", "columns": 1, "traits": []},
    }
    return a2a_task("COMPLETED", artifact_parts=[{"data": reply}])


async def test_a_resume_syncs_the_profile_without_making_a_document(client, harness):
    imported = await _import(
        client, harness, resume_reply(), b"%PDF-1.7 resume", name="cv.pdf"
    )

    assert imported.status_code == 201
    assert harness.received[0].url.path == "/ezcareer/a2a/import-resume"
    assert (await client.get(f"{PREFIX}/documents")).json() == []
    profile = (await client.get(PROFILE)).json()
    assert (profile["name"], profile["headline"], profile["email"]) == (
        "Kelvin Chong",
        "Backend engineer",
        "k@example.com",
    )
    assert profile["links"] == [
        {"label": "LinkedIn", "url": "https://linkedin.com/in/kelvin"}
    ]
    entries = {e["title"]: e for e in (await client.get(f"{PROFILE}/entries")).json()}
    assert entries["Senior Engineer"]["start"] == "2022-01"
    assert entries["Senior Engineer"]["highlights"] == ["Cut deploys to 5 min."]
    assert entries["Renderverse"]["code_link"] == "https://github.com/k/rv"
    assert entries["Renderverse"]["link"] == "https://kelvinchong.dev"
    assert entries["Renderverse"]["tools"] == ["React"]
    skills = (await client.get(f"{PROFILE}/skills")).json()
    assert {(s["group"], s["name"]) for s in skills} == {
        ("Languages", "Python"),
        ("Spoken languages", "Malay"),
    }


async def test_a_failed_import_adds_nothing(client, harness):
    reason = "The file has no text to read"

    failed = await _import(
        client,
        harness,
        a2a_task("FAILED", status_parts=[{"text": reason}]),
        b"%PDF-1.7",
        name="cv.pdf",
    )

    assert failed.status_code == 422
    assert failed.json()["detail"] == reason
    assert (await client.get(f"{PROFILE}/imports")).json() == []


async def test_only_resumes_and_exports_are_imported(client, harness):
    image = await client.post(
        f"{PROFILE}/imports", files={"file": ("me.png", b"png", "image/png")}
    )
    not_zip = await client.post(
        f"{PROFILE}/imports", files={"file": ("x.zip", b"not a zip", "application/zip")}
    )
    no_profile = await client.post(
        f"{PROFILE}/imports",
        files={"file": ("x.zip", _export(Messages="a\n1\n"), "application/zip")},
    )

    assert [r.status_code for r in (image, not_zip, no_profile)] == [422, 422, 422]
    assert not_zip.json()["detail"] == "The file is not a zip archive"
    assert harness.received == []


def test_an_export_unpacking_past_the_cap_is_refused():
    with pytest.raises(UnreadableExport):
        read_export(_export(Positions=POSITIONS * 100), max_unzipped_bytes=1000)


@pytest.mark.postgres
@pytest.mark.skipif(not DATABASE_URL, reason="OPS_API_TEST_DATABASE_URL is not set")
async def test_imports_and_their_changes_round_trip_on_postgres(postgres_app, harness):
    async with _client(postgres_app) as client:
        await client.post(f"{PROFILE}/entries", json=ACME | {"highlights": ["Led it."]})
        await _import(
            client,
            harness,
            _profile(ACME | {"highlights": ["Cut deploys to 5 minutes."]}),
            _export("one", Positions=POSITIONS),
        )
        await client.post(
            f"{PROFILE}/entries", json=ACME | {"organisation": "Globex Inc."}
        )
        await _import(
            client,
            harness,
            _profile(ACME | {"organisation": "Globex", "summary": "Other"}),
            _export("two", Positions=POSITIONS),
        )
        changes = await _changes(client)

    assert [(c["kind"], c.get("field")) for c in changes] == [
        ("field", "highlights"),
        ("match", None),
    ]
    assert changes[0]["current"] == ["Led it."]
    assert changes[0]["conflict"] == ["Cut deploys to 5 minutes."]
    assert changes[1]["entry"]["organisation"] == "Globex"
