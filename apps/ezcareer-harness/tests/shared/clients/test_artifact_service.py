import json
from base64 import b64encode
from hashlib import sha256

import httpx
import pytest
from document_schema import DocumentKind, ResumeDocument

from tests.fakes import artifact_service

DOCUMENT = ResumeDocument.model_validate(
    {
        "kind": DocumentKind.RESUME,
        "content": {
            "blocks": [{"kind": "profile", "id": "profile", "name": {"text": "Ada"}}]
        },
    }
)


async def test_render_posts_the_document_template_and_assets():
    requests: list[httpx.Request] = []
    photo = b"png bytes"

    rendered = await artifact_service(requests).render(
        DOCUMENT, {"id": "classic"}, {sha256(photo).hexdigest(): photo}
    )

    [request] = requests
    assert request.url == "http://artifact-service.test/artifact-service/v1/render"
    assert json.loads(request.content) == {
        "document": DOCUMENT.model_dump(mode="json"),
        "template": {"id": "classic"},
        "assets": {sha256(photo).hexdigest(): b64encode(photo).decode()},
    }
    assert rendered.artifact == b"%PDF-fake"
    assert rendered.report.pages == 1


async def test_a_rejected_render_raises():
    with pytest.raises(httpx.HTTPStatusError):
        await artifact_service([], status=422).render(DOCUMENT, {"id": "classic"}, {})
