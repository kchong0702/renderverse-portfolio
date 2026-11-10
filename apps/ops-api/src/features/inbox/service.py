from __future__ import annotations

import html
import re
from base64 import urlsafe_b64encode
from email.message import EmailMessage
from email.utils import parseaddr
from html.parser import HTMLParser
from uuid import UUID

from src.clients.google import GmailMessage, GmailPart, GmailSend, GoogleClient
from src.core.config import GoogleSettings
from src.core.exceptions import InvalidInput
from src.features.google import GoogleService
from src.features.inbox.schemas import (
    EmailCreate,
    InboxMessage,
    InboxMessageDetail,
    ReplyCreate,
)


def _summary(message: GmailMessage) -> InboxMessage:
    """The list row for a Gmail message"""
    name, email = parseaddr(message.payload.header("From"))
    return InboxMessage(
        id=message.id,
        thread_id=message.thread_id,
        from_name=name or email,
        from_email=email,
        subject=message.payload.header("Subject"),
        snippet=html.unescape(message.snippet),
        received_at=message.internal_date,
        unread="UNREAD" in message.label_ids,
    )


class _TextParser(HTMLParser):
    def __init__(self):
        """Collect an HTML body's text, leaving out styles and scripts"""
        super().__init__()
        self.parts: list[str] = []
        self._hidden = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Hide a style or script's text; a br starts a new line"""
        if tag in ("style", "script"):
            self._hidden = True
        elif tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        """Show text again after a style or script; a block ends its line"""
        if tag in ("style", "script"):
            self._hidden = False
        elif tag in ("p", "div", "tr", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        """Keep text that is not inside a style or script"""
        if not self._hidden:
            self.parts.append(data)


def _html_text(markup: str) -> str:
    """The readable text of an HTML body: no styles, scripts or tags"""
    parser = _TextParser()
    parser.feed(markup)
    parser.close()
    return re.sub(r"\n\s*\n+", "\n\n", "".join(parser.parts)).strip()


def _mime(to: str, subject: str, body: str, answers: GmailPart | None = None) -> str:
    """An email as Gmail's send takes it, RFC 2822 and base64url encoded; a reply
    names the message it answers so mail clients thread it"""
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    if answers is not None:
        message_id = answers.header("Message-ID")
        message["In-Reply-To"] = message_id
        message["References"] = f"{answers.header('References')} {message_id}".strip()
    message.set_content(body)
    return urlsafe_b64encode(message.as_bytes()).decode()


class InboxService:
    def __init__(
        self, google: GoogleService, client: GoogleClient, settings: GoogleSettings
    ):
        """Read Gmail with the user's token, keeping to the job-search query"""
        self._google = google
        self._client = client
        self._settings = settings

    async def messages(self, user_id: UUID) -> list[InboxMessage]:
        """The newest emails that match the job-search query"""
        token = await self._google.access_token(user_id)
        found = await self._client.messages(
            token, self._settings.inbox_query, self._settings.inbox_limit
        )
        return [_summary(message) for message in found]

    async def message(self, user_id: UUID, message_id: str) -> InboxMessageDetail:
        """One email with its body as plain text"""
        token = await self._google.access_token(user_id)
        message = await self._client.message(token, message_id)
        payload = message.payload
        return InboxMessageDetail(
            **_summary(message).model_dump(),
            to=payload.header("To"),
            body=payload.find("text/plain").strip()
            or _html_text(payload.find("text/html")),
        )

    async def reply(self, user_id: UUID, thread_id: str, reply: ReplyCreate) -> None:
        """Answer the newest email in the thread that someone else sent, in the thread"""
        token = await self._google.access_token(user_id)
        thread = await self._client.thread(token, thread_id)
        me = (await self._google.email(user_id) or "").lower()
        theirs = [
            m.payload
            for m in thread.messages
            if parseaddr(m.payload.header("From"))[1].lower() != me
        ]
        if not theirs:
            raise InvalidInput(
                "Nobody else wrote in this thread, so there is no one to reply to"
            )
        subject = thread.messages[0].payload.header("Subject")
        await self._client.send(
            token,
            GmailSend(
                raw=_mime(
                    theirs[-1].header("Reply-To") or theirs[-1].header("From"),
                    subject if subject.lower().startswith("re:") else f"Re: {subject}",
                    reply.body,
                    theirs[-1],
                ),
                thread_id=thread_id,
            ),
        )

    async def send(self, user_id: UUID, email: EmailCreate) -> None:
        """Send a new email from the user's Gmail"""
        token = await self._google.access_token(user_id)
        await self._client.send(
            token, GmailSend(raw=_mime(email.to, email.subject, email.body))
        )


__all__ = ["InboxService"]
