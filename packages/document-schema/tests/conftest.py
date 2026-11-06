from typing import Any


def value(text: str) -> dict[str, Any]:
    return {"text": text, "src": ["p1.s1"]}


def rich(html: str) -> dict[str, Any]:
    return {"html": html, "src": ["p1.s2"]}
