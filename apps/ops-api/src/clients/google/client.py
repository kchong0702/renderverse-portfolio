from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode

import httpx2
from pydantic import BaseModel, ValidationError

from src.clients.google.schemas import (
    EventList,
    EventMove,
    GmailList,
    GmailMessage,
    GmailProfile,
    GmailSend,
    GmailSent,
    GmailThread,
    GmailThreadList,
    GoogleEvent,
    NewEvent,
    Tokens,
)
from src.core.config import GoogleSettings
from src.core.exceptions import AlreadyExists, Conflict, NotFound, ServiceUnavailable
from src.core.logging import get_logger

RECONNECT = "Google access expired or was revoked; reconnect Google in Settings"
"""Why a request needs the user to connect Google again"""

MISSING_SCOPE = (
    "Ops now sends email and adds Calendar events, which your Google connection "
    "does not allow yet; reconnect Google in Settings"
)
"""Why a write needs a connection made before Ops asked to send and add events"""

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
_CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"

logger = get_logger(__name__)


def _parse[T: BaseModel](response: httpx2.Response, model: type[T]) -> T:
    """A successful response's JSON as model; ServiceUnavailable for anything else"""
    if response.is_error:
        logger.warning(
            "google_error", status_code=response.status_code, body=response.text
        )
        raise ServiceUnavailable("Google answered with an error; try again later")
    try:
        return model.model_validate_json(response.content)
    except ValidationError as error:
        raise ServiceUnavailable("Google sent a response Ops cannot read") from error


class GoogleClient:
    def __init__(
        self,
        settings: GoogleSettings,
        transport: httpx2.AsyncBaseTransport | None = None,
    ):
        """One HTTP client for the app's lifetime; tests pass a mock transport"""
        self._settings = settings
        self._http = httpx2.AsyncClient(
            timeout=settings.timeout_seconds, transport=transport
        )

    async def _send(
        self,
        method: str,
        url: str,
        *,
        data: dict[str, str] | None = None,
        params: list[tuple[str, str]] | None = None,
        token: str | None = None,
        body: BaseModel | None = None,
    ) -> httpx2.Response:
        """One request to Google; ServiceUnavailable when Google cannot be reached"""
        try:
            return await self._http.request(
                method,
                url,
                data=data,
                params=params,
                json=body.model_dump(mode="json", by_alias=True, exclude_none=True)
                if body
                else None,
                headers={"Authorization": f"Bearer {token}"} if token else None,
            )
        except httpx2.HTTPError as error:
            raise ServiceUnavailable(
                "Google could not be reached; try again later"
            ) from error

    async def _token(self, form: dict[str, str]) -> Tokens:
        """POST to the token endpoint with the OAuth client's credentials"""
        response = await self._send(
            "POST",
            _TOKEN_URL,
            data={
                **form,
                "client_id": self._settings.client_id,
                "client_secret": self._settings.client_secret.get_secret_value(),
            },
        )
        if response.status_code == 400 and b"invalid_grant" in response.content:
            raise Conflict(RECONNECT)
        return _parse(response, Tokens)

    async def _call[T: BaseModel](
        self,
        method: str,
        url: str,
        token: str,
        model: type[T],
        params: list[tuple[str, str]] | None = None,
        body: BaseModel | None = None,
    ) -> T:
        """Call a Google API as the user and parse the JSON into model"""
        response = await self._send(method, url, params=params, token=token, body=body)
        if response.status_code == 401:
            raise Conflict(RECONNECT)
        if (
            response.status_code == 403
            and b"insufficientPermissions" in response.content
        ):
            raise Conflict(MISSING_SCOPE)
        if response.status_code == 404:
            raise NotFound("Google has no such item")
        if response.status_code == 409 and b"duplicate" in response.content:
            raise AlreadyExists("Google already has an item with this id")
        return _parse(response, model)

    def authorize_url(self, state: str) -> str:
        """Google's consent page for Gmail and Calendar, with offline access"""
        query = urlencode(
            {
                "client_id": self._settings.client_id,
                "redirect_uri": self._settings.redirect_uri,
                "response_type": "code",
                "scope": " ".join(self._settings.scopes),
                "access_type": "offline",
                "prompt": "consent",
                "include_granted_scopes": "true",
                "state": state,
            }
        )
        return f"{_AUTHORIZE_URL}?{query}"

    async def exchange_code(self, code: str) -> Tokens:
        """Trade the callback's code for an access and a refresh token"""
        return await self._token(
            {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": self._settings.redirect_uri,
            }
        )

    async def refresh(self, refresh_token: str) -> str:
        """A fresh access token; Conflict when the refresh token no longer works"""
        tokens = await self._token(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )
        return tokens.access_token

    async def revoke(self, token: str) -> None:
        """End the user's grant; a token Google already dropped counts as revoked"""
        response = await self._send("POST", _REVOKE_URL, data={"token": token})
        if response.is_error and response.status_code != 400:
            raise ServiceUnavailable("Google did not revoke access; try again later")

    async def email(self, access_token: str) -> str:
        """The Gmail address the token reads"""
        profile = await self._call(
            "GET", f"{_GMAIL_URL}/profile", access_token, GmailProfile
        )
        return profile.email_address

    async def messages(
        self, access_token: str, query: str, limit: int
    ) -> list[GmailMessage]:
        """The newest messages matching a Gmail search, with headers but no body;
        leaves out any deleted between the search and the fetch"""
        found = await self._call(
            "GET",
            f"{_GMAIL_URL}/messages",
            access_token,
            GmailList,
            [("q", query), ("maxResults", str(limit))],
        )
        metadata = [
            ("format", "metadata"),
            ("metadataHeaders", "From"),
            ("metadataHeaders", "Subject"),
        ]
        messages = await asyncio.gather(
            *(
                self._call(
                    "GET",
                    f"{_GMAIL_URL}/messages/{ref.id}",
                    access_token,
                    GmailMessage,
                    metadata,
                )
                for ref in found.messages
            ),
            return_exceptions=True,
        )
        for message in messages:
            if isinstance(message, BaseException) and not isinstance(message, NotFound):
                raise message
        return [message for message in messages if isinstance(message, GmailMessage)]

    async def message(self, access_token: str, message_id: str) -> GmailMessage:
        """One message with its whole MIME tree"""
        return await self._call(
            "GET",
            f"{_GMAIL_URL}/messages/{message_id}",
            access_token,
            GmailMessage,
            [("format", "full")],
        )

    async def thread(self, access_token: str, thread_id: str) -> GmailThread:
        """One conversation with every message's MIME tree, oldest first"""
        return await self._call(
            "GET",
            f"{_GMAIL_URL}/threads/{thread_id}",
            access_token,
            GmailThread,
            [("format", "full")],
        )

    async def threads(
        self, access_token: str, query: str, limit: int
    ) -> tuple[list[GmailThread], int]:
        """The newest threads matching a Gmail search with every message's MIME tree,
        and Gmail's estimate of how many match; leaves out any deleted meanwhile"""
        found = await self._call(
            "GET",
            f"{_GMAIL_URL}/threads",
            access_token,
            GmailThreadList,
            [("q", query), ("maxResults", str(limit))],
        )
        threads = await asyncio.gather(
            *(self.thread(access_token, ref.id) for ref in found.threads),
            return_exceptions=True,
        )
        for thread in threads:
            if isinstance(thread, BaseException) and not isinstance(thread, NotFound):
                raise thread
        return [
            thread for thread in threads if isinstance(thread, GmailThread)
        ], found.result_size_estimate

    async def send(self, access_token: str, message: GmailSend) -> None:
        """Send an email from the user's Gmail, in a thread when it names one"""
        await self._call(
            "POST",
            f"{_GMAIL_URL}/messages/send",
            access_token,
            GmailSent,
            body=message,
        )

    async def events(
        self, access_token: str, start: datetime, end: datetime
    ) -> EventList:
        """Events on the primary calendar that overlap the range, repeats expanded,
        with the calendar's time zone"""
        return await self._call(
            "GET",
            _CALENDAR_URL,
            access_token,
            EventList,
            [
                ("timeMin", start.isoformat()),
                ("timeMax", end.isoformat()),
                ("singleEvents", "true"),
                ("orderBy", "startTime"),
                ("maxResults", str(self._settings.calendar_max_events)),
            ],
        )

    async def create_event(self, access_token: str, event: NewEvent) -> GoogleEvent:
        """Add an event to the primary calendar"""
        return await self._call(
            "POST", _CALENDAR_URL, access_token, GoogleEvent, body=event
        )

    async def move_event(
        self, access_token: str, event_id: str, move: EventMove
    ) -> GoogleEvent:
        """Give an event on the primary calendar a new start and end"""
        return await self._call(
            "PATCH", f"{_CALENDAR_URL}/{event_id}", access_token, GoogleEvent, body=move
        )

    async def delete_event(self, access_token: str, event_id: str) -> None:
        """Remove an event from the primary calendar; one Google no longer has counts
        as removed"""
        response = await self._send(
            "DELETE", f"{_CALENDAR_URL}/{event_id}", token=access_token
        )
        if response.status_code == 401:
            raise Conflict(RECONNECT)
        if response.is_error and response.status_code not in (404, 410):
            logger.warning(
                "google_error", status_code=response.status_code, body=response.text
            )
            raise ServiceUnavailable("Google did not remove the event; try again later")

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["MISSING_SCOPE", "RECONNECT", "GoogleClient"]
