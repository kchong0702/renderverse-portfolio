from base64 import urlsafe_b64decode
from email import message_from_bytes, policy
from email.message import EmailMessage

from src.clients.google.client import MISSING_SCOPE
from tests.conftest import PREFIX, connect_google


def _message(key: str, sender: str, headers: dict[str, str]) -> dict[str, object]:
    """A Gmail message of thread t-1"""
    return {
        "id": key,
        "threadId": "t-1",
        "internalDate": "1762650720000",
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": "Final round with Lumen Pay"},
                *({"name": k, "value": v} for k, v in headers.items()),
            ],
        },
    }


def _sent(raw: str) -> EmailMessage:
    """The email Gmail was asked to send"""
    message = message_from_bytes(urlsafe_b64decode(raw), policy=policy.default)
    assert isinstance(message, EmailMessage)
    return message


async def test_a_reply_goes_in_the_thread_to_the_last_other_sender(client, google):
    await connect_google(client)
    google.messages = {
        "m3": _message("m3", "Kelvin <kelvin@gmail.com>", {"Message-ID": "<c@x>"}),
        "m2": _message(
            "m2",
            "Aisha Rahman <aisha@lumenpay.com>",
            {"Message-ID": "<b@x>", "References": "<a@x>"},
        ),
        "m1": _message("m1", "Aisha Rahman <aisha@lumenpay.com>", {}),
    }

    response = await client.post(
        f"{PREFIX}/inbox/t-1/reply", json={"body": "Tuesday at 10 works."}
    )

    assert response.status_code == 204
    [sent] = google.sent
    assert sent["threadId"] == "t-1"
    email = _sent(sent["raw"])
    assert email["To"] == "Aisha Rahman <aisha@lumenpay.com>"
    assert email["Subject"] == "Re: Final round with Lumen Pay"
    assert email["In-Reply-To"] == "<b@x>"
    assert email["References"] == "<a@x> <b@x>"
    assert email.get_content().strip() == "Tuesday at 10 works."


async def test_a_thread_only_the_user_wrote_in_has_no_one_to_reply_to(client, google):
    await connect_google(client)
    google.messages = {"m1": _message("m1", "kelvin@gmail.com", {})}

    response = await client.post(f"{PREFIX}/inbox/t-1/reply", json={"body": "Hi"})

    assert response.status_code == 422
    assert google.sent == []


async def test_compose_sends_a_new_email(client, google):
    await connect_google(client)

    response = await client.post(
        f"{PREFIX}/inbox/compose",
        json={
            "to": "talent@northwind.dev",
            "subject": "Backend Engineer application",
            "body": "Hi, I applied last week.",
        },
    )

    assert response.status_code == 204
    [sent] = google.sent
    assert "threadId" not in sent
    email = _sent(sent["raw"])
    assert email["To"] == "talent@northwind.dev"
    assert email["Subject"] == "Backend Engineer application"
    assert email["In-Reply-To"] is None
    assert email.get_content().strip() == "Hi, I applied last week."


async def test_compose_needs_an_address(client, google):
    await connect_google(client)

    response = await client.post(
        f"{PREFIX}/inbox/compose",
        json={"to": "Northwind", "subject": "Hi", "body": "Hi"},
    )

    assert response.status_code == 422
    assert google.sent == []


async def test_a_read_only_grant_asks_to_reconnect_for_sending(client, google):
    await connect_google(client)
    google.read_only = True

    response = await client.post(
        f"{PREFIX}/inbox/compose",
        json={"to": "talent@northwind.dev", "subject": "Hi", "body": "Hi"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": MISSING_SCOPE}
