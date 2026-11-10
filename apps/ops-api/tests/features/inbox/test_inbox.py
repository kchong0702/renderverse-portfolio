from base64 import urlsafe_b64encode

from src.core.config import get_settings
from tests.conftest import PREFIX, a2a_task, connect_google

INFO = a2a_task(
    "COMPLETED",
    artifact_parts=[
        {
            "data": {
                "state": "info",
                "application_id": None,
                "decide_by": None,
                "interview": None,
            }
        }
    ],
)


def _data(text: str) -> dict[str, str]:
    """A Gmail body holding text"""
    return {"data": urlsafe_b64encode(text.encode()).decode().rstrip("=")}


def _message(
    key: str, subject: str, parts: list[dict[str, object]]
) -> dict[str, object]:
    """A Gmail message as the API returns it"""
    return {
        "id": key,
        "threadId": f"t-{key}",
        "labelIds": ["INBOX", "UNREAD"] if key == "m1" else ["INBOX"],
        "snippet": "Hi Kelvin, thanks for the technical round &amp; more",
        "internalDate": "1762650720000",
        "payload": {
            "mimeType": "multipart/alternative",
            "headers": [
                {"name": "From", "value": "Aisha Rahman <aisha@lumenpay.com>"},
                {"name": "To", "value": "kelvin@gmail.com"},
                {"name": "Subject", "value": subject},
            ],
            "parts": parts,
        },
    }


async def test_inbox_lists_the_job_search_emails(client, google, harness):
    await connect_google(client)
    google.messages = {
        "m1": _message("m1", "Final round with Lumen Pay", []),
        "m2": _message("m2", "Your offer letter", []),
    }
    harness.outcomes = [INFO, INFO]

    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 200
    assert response.json()["needs_reply"] == 0
    assert response.json()["messages"] == [
        {
            "id": "m1",
            "thread_id": "t-m1",
            "from_name": "Aisha Rahman",
            "from_email": "aisha@lumenpay.com",
            "subject": "Final round with Lumen Pay",
            "snippet": "Hi Kelvin, thanks for the technical round & more",
            "received_at": "2025-11-09T01:12:00Z",
            "unread": True,
            "state": "info",
            "decide_by": None,
            "application_id": None,
            "on_calendar": False,
        },
        {
            "id": "m2",
            "thread_id": "t-m2",
            "from_name": "Aisha Rahman",
            "from_email": "aisha@lumenpay.com",
            "subject": "Your offer letter",
            "snippet": "Hi Kelvin, thanks for the technical round & more",
            "received_at": "2025-11-09T01:12:00Z",
            "unread": False,
            "state": "info",
            "decide_by": None,
            "application_id": None,
            "on_calendar": False,
        },
    ]
    assert google.gmail_queries == [get_settings().google.inbox_query]
    assert google.refreshed_with == ["refresh-1"]


async def test_a_message_deleted_after_the_search_is_left_out(client, google, harness):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "Final round with Lumen Pay", [])}
    google.deleted = ["gone"]
    harness.outcomes = [INFO]

    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 200
    assert [message["id"] for message in response.json()["messages"]] == ["m1"]


async def test_a_message_has_its_plain_text_body(client, google):
    await connect_google(client)
    google.messages = {
        "m1": _message(
            "m1",
            "Final round",
            [
                {"mimeType": "text/plain", "body": _data("Could you share times?")},
                {"mimeType": "text/html", "body": _data("<p>Could you</p>")},
            ],
        ),
        "m2": _message(
            "m2",
            "Offer",
            [
                {
                    "mimeType": "text/html",
                    "body": _data(
                        "<style>p{}</style><p>Your offer</p>"
                        "<p>Salary &amp; start<br/>Monday</p><script>x()</script>"
                    ),
                }
            ],
        ),
    }

    plain = await client.get(f"{PREFIX}/inbox/m1")
    html_only = await client.get(f"{PREFIX}/inbox/m2")

    assert plain.status_code == 200
    assert plain.json()["body"] == "Could you share times?"
    assert plain.json()["to"] == "kelvin@gmail.com"
    assert html_only.json()["body"] == "Your offer\nSalary & start\nMonday"


async def test_an_unknown_message_is_not_found(client):
    await connect_google(client)

    response = await client.get(f"{PREFIX}/inbox/nope")

    assert response.status_code == 404


async def test_inbox_before_connecting_asks_to_connect(client):
    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 409
    assert response.json() == {"detail": "Connect a Google account in Settings first"}


async def test_a_revoked_grant_asks_to_reconnect(client, google):
    await connect_google(client)
    google.revoked = True

    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Google access expired or was revoked; reconnect Google in Settings"
    }


async def test_a_google_error_hides_its_body(client, google):
    await connect_google(client)
    google.failing = True

    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Google answered with an error; try again later"
    }


async def test_google_unreachable_is_a_clear_error(client, google):
    await connect_google(client)
    google.down = True

    response = await client.get(f"{PREFIX}/inbox")

    assert response.status_code == 503
    assert response.json() == {"detail": "Google could not be reached; try again later"}
