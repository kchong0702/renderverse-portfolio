from __future__ import annotations

from typing import Any

import pytest

FONT_SHA = "a" * 64
RENDER_ID = "b" * 64

LAYOUT_TOKENS = {
    "--page-margin-top": "14mm",
    "--page-margin-right": "16mm",
    "--page-margin-bottom": "14mm",
    "--page-margin-left": "16mm",
    "--font-size-body": "10.5pt",
    "--line-height": "1.35",
    "--section-gap": "14pt",
}

RESUME_TOKENS = {**LAYOUT_TOKENS, "--item-gap": "8pt", "--bullet-gap": "2pt"}


@pytest.fixture
def resume() -> dict[str, Any]:
    return {
        "kind": "resume",
        "content": {
            "header": {
                "name": {"text": "Ada Lovelace", "src": ["p1.s1"]},
                "headline": {"text": "Analytical Engine Programmer", "src": ["p1.s2"]},
                "contact": [
                    {
                        "id": "c_1",
                        "kind": "email",
                        "value": {"text": "ada@example.com", "src": ["p1.s3"]},
                    },
                    {
                        "id": "c_2",
                        "kind": "location",
                        "value": {"text": "London", "src": ["fact:home-city"]},
                    },
                ],
            },
            "sections": [
                {
                    "id": "sec_1",
                    "kind": "experience",
                    "heading": {"text": "EMPLOYMENT HISTORY", "src": ["p1.s10"]},
                    "items": [
                        {
                            "id": "it_1",
                            "title": {"text": "Programmer", "src": ["p1.s11"]},
                            "organization": {"text": "Babbage & Co", "src": ["p1.s12"]},
                            "period": {"text": "1842 - 1843", "src": ["p1.s13"]},
                            "details": [
                                {
                                    "id": "d_1",
                                    "label": "Team size",
                                    "value": {
                                        "text": "2",
                                        "src": [
                                            "user:sections/sec_1/items/it_1/details/d_1/value"
                                        ],
                                    },
                                }
                            ],
                            "bullets": [
                                {
                                    "id": "b_1",
                                    "text": {
                                        "text": "Wrote the first published algorithm",
                                        "src": ["p1.s14"],
                                    },
                                },
                                {
                                    "id": "b_2",
                                    "text": {
                                        "text": "Annotated Menabrea's notes",
                                        "src": ["p1.s15"],
                                    },
                                },
                            ],
                            "tags": [
                                {
                                    "id": "t_1",
                                    "text": {"text": "Punch cards", "src": ["p1.s16"]},
                                }
                            ],
                            "links": [
                                {
                                    "id": "l_1",
                                    "url": {
                                        "text": "https://github.com/ada/engine",
                                        "src": ["p1.s17"],
                                    },
                                    "label": {"text": "GitHub", "src": ["p1.s17"]},
                                }
                            ],
                        }
                    ],
                },
                {
                    "id": "sec_2",
                    "kind": "skills",
                    "heading": {"text": "SKILLS", "src": ["p1.s20"]},
                    "tags": [
                        {
                            "id": "t_1",
                            "text": {"text": "Mathematics", "src": ["p1.s21"]},
                        },
                        {
                            "id": "t_2",
                            "text": {"text": "Punch cards", "src": ["p1.s22"]},
                        },
                    ],
                },
            ],
        },
        "template": {
            "html": (
                '<h1 data-field="{{header.name.path}}">{{header.name.text}}</h1>'
                "{{#sections}}<section>{{#items}}"
                '<h2 data-field="{{title.path}}">{{title.text}}</h2>'
                "{{/items}}</section>{{/sections}}"
            ),
            "css": "h1 { color: var(--accent); font-family: Inter; }",
            "tokens": {**RESUME_TOKENS, "--accent": "#1f3a5f", "--muted": "#6b7280"},
        },
        "presentation": {
            "page_size": "a4",
            "token_overrides": {"--accent": "#1a2b3c"},
            "fonts": [
                {
                    "family": "Inter",
                    "weight": 400,
                    "style": "normal",
                    "sha256": FONT_SHA,
                }
            ],
            "hidden": [],
        },
        "assets": {
            FONT_SHA: {
                "media_type": "font/woff2",
                "uri": "s3://assets/inter-400.woff2",
            }
        },
    }


@pytest.fixture
def cover_letter() -> dict[str, Any]:
    return {
        "kind": "cover_letter",
        "content": {
            "header": {
                "name": {"text": "Ada Lovelace"},
                "contact": [
                    {"id": "c_1", "kind": "email", "value": {"text": "ada@example.com"}}
                ],
            },
            "sections": [
                {
                    "id": "p_1",
                    "kind": "custom",
                    "text": {"text": "Dear hiring manager,", "src": ["fact:greeting"]},
                },
                {
                    "id": "p_2",
                    "kind": "custom",
                    "text": {"text": "I would like to apply for the role."},
                },
            ],
        },
        "template": {
            "html": '{{#sections}}<p data-field="sections/{{id}}/text">{{text.text}}</p>{{/sections}}',
            "css": "p { margin: 0 0 1em; }",
            "tokens": LAYOUT_TOKENS,
        },
    }
