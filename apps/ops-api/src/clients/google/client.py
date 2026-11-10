from __future__ import annotations

import asyncio
from datetime import datetime
from urllib.parse import urlencode

import httpx2
from pydantic import BaseModel, ValidationError

from src.clients.google.schemas import (
    EventList,
    GmailList,
    GmailMessage,
    GmailProfile,
    GoogleEvent,
    Tokens,
)
from src.core.config import GoogleSettings
from src.core.exceptions import Conflict, NotFound, ServiceUnavailable

SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)
"""Read-only Gmail and Calendar, the only access Ops asks for"""

RECONNECT = "Google access expired or was revoked; reconnect Google in Settings"
"""Why a request needs the user to connect Google again"""

_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
_GMAIL_URL = "https://gmail.googleapis.com/gmail/v1/users/me"
_CALENDAR_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"


def _parse[T: BaseModel](response: httpx2.Response, model: type[T]) -> T:
    """A successful response's JSON as model; ServiceUnavailable for anything else"""
    if response.is_error:
        raise ServiceUnavailable(
            f"Google answered {response.status_code}: {response.text[:300]}"
        )
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
    ) -> httpx2.Response:
        """One request to Google; ServiceUnavailable when Google cannot be reached"""
        try:
            return await self._http.request(
                method,
                url,
                data=data,
                params=params,
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

    async def _get[T: BaseModel](
        self,
        url: str,
        token: str,
        model: type[T],
        params: list[tuple[str, str]] | None = None,
    ) -> T:
        """GET a Google API as the user and parse the JSON into model"""
        response = await self._send("GET", url, params=params, token=token)
        if response.status_code == 401:
            raise Conflict(RECONNECT)
        if response.status_code == 404:
            raise NotFound("Google has no such item")
        return _parse(response, model)

    def authorize_url(self, state: str) -> str:
        """Google's consent page for read-only Gmail and Calendar, with offline access"""
        query = urlencode(
            {
                "client_id": self._settings.client_id,
                "redirect_uri": self._settings.redirect_uri,
                "response_type": "code",
                "scope": " ".join(SCOPES),
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
        profile = await self._get(f"{_GMAIL_URL}/profile", access_token, GmailProfile)
        return profile.email_address

    async def messages(
        self, access_token: str, query: str, limit: int
    ) -> list[GmailMessage]:
        """The newest messages matching a Gmail search, with headers but no body;
        leaves out any deleted between the search and the fetch"""
        found = await self._get(
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
                self._get(
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
        return await self._get(
            f"{_GMAIL_URL}/messages/{message_id}",
            access_token,
            GmailMessage,
            [("format", "full")],
        )

    async def events(
        self, access_token: str, start: datetime, end: datetime
    ) -> list[GoogleEvent]:
        """Events on the primary calendar that overlap the range, repeats expanded"""
        found = await self._get(
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
        return found.items

    async def aclose(self) -> None:
        """Close the HTTP client's connections"""
        await self._http.aclose()


__all__ = ["RECONNECT", "SCOPES", "GoogleClient"]
