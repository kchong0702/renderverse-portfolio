from __future__ import annotations

import html
import re
from email.utils import parseaddr
from html.parser import HTMLParser
from uuid import UUID

from src.clients.google import GmailMessage, GoogleClient
from src.core.config import GoogleSettings
from src.features.google import GoogleService
from src.features.inbox.schemas import InboxMessage, InboxMessageDetail


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


__all__ = ["InboxService"]
