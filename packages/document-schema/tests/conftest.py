from typing import Any

import pytest

PHOTO = "a" * 64
SIGNATURE = "b" * 64


def value(text: str) -> dict[str, Any]:
    return {"text": text, "src": ["p1.s1"]}


def rich(html: str) -> dict[str, Any]:
    return {"html": html, "src": ["p1.s2"]}


@pytest.fixture
def resume() -> dict[str, Any]:
    return {
        "kind": "resume",
        "content": {
            "blocks": [
                {
                    "kind": "profile",
                    "id": "profile",
                    "name": value("Kelvin Chong"),
                    "headline": value("Senior Engineer"),
                },
                {"kind": "photo", "id": "photo", "file": PHOTO},
                {
                    "kind": "contacts",
                    "id": "contacts",
                    "items": [
                        {
                            "id": "c1",
                            "kind": "email",
                            "value": value("kelvin@example.com"),
                        },
                        {
                            "id": "c2",
                            "kind": "github",
                            "value": value("github.com/kelvin"),
                        },
                    ],
                },
                {
                    "kind": "summary",
                    "id": "sum",
                    "text": rich("Backend engineer with <b>7 years</b> of payments."),
                },
                {
                    "kind": "experience",
                    "id": "exp",
                    "items": [
                        {
                            "id": "acme",
                            "role": value("Senior Engineer"),
                            "company": value("Acme Corp"),
                            "dates": {
                                "text": value("2022 to now"),
                                "start": "2022",
                                "end": "present",
                            },
                            "bullets": [
                                {
                                    "id": "b1",
                                    "text": rich("Led the migration of 30 services."),
                                }
                            ],
                        }
                    ],
                },
                {
                    "kind": "skills",
                    "id": "sk",
                    "items": [
                        {
                            "id": "s1",
                            "label": value("Languages"),
                            "items": [{"id": "t1", "text": value("Python")}],
                        }
                    ],
                },
            ]
        },
        "design": {
            "template": "sidebar-band",
            "layouts": [
                {
                    "template": "sidebar-band",
                    "region": "side",
                    "blocks": ["photo", "profile", "sk"],
                }
            ],
        },
        "assets": {PHOTO: {"media_type": "image/png", "uri": "s3://assets/photo.png"}},
    }


@pytest.fixture
def letter() -> dict[str, Any]:
    return {
        "kind": "cover_letter",
        "content": {
            "blocks": [
                {"kind": "profile", "id": "profile", "name": value("Kelvin Chong")},
                {
                    "kind": "recipient",
                    "id": "to",
                    "name": value("Aisha Rahman"),
                    "organization": value("Lumen Pay"),
                },
                {
                    "kind": "letter",
                    "id": "letter",
                    "greeting": value("Dear Ms Rahman,"),
                    "paragraphs": [
                        {"id": "p1", "text": rich("I would like to apply.")}
                    ],
                    "closing": value("Yours sincerely,"),
                    "signature": SIGNATURE,
                },
            ]
        },
        "assets": {
            SIGNATURE: {"media_type": "image/png", "uri": "s3://assets/signature.png"}
        },
    }
