from __future__ import annotations


class OAuthFailed(Exception):
    """Sign-in with a provider was cancelled, expired or rejected; the router sends
    the user back to the sign-in page, so it never becomes an HTTP error"""


__all__ = ["OAuthFailed"]
