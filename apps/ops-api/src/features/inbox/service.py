from __future__ import annotations

import html
import re
from email.utils import parseaddr
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


def _html_text(markup: str) -> str:
    """The readable text of an HTML body: no styles, scripts or tags"""
    markup = re.sub(r"(?is)<(style|script)\b.*?</\1>", "", markup)
    markup = re.sub(r"(?i)<br\s*/?>|</(p|div|tr|h\d|li)>", "\n", markup)
    text = html.unescape(re.sub(r"<[^>]+>", "", markup))
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()


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
