from __future__ import annotations

from pwdlib import PasswordHash

MIN_PASSWORD_LENGTH = 12

_hasher = PasswordHash.recommended()

_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(
    password: str, password_hash: str | None
) -> tuple[bool, str | None]:
    """Whether it matches, and a new hash when the stored one uses old parameters"""
    if password_hash is None:
        _hasher.verify(password, _DUMMY_HASH)
        return False, None
    return _hasher.verify_and_update(password, password_hash)


__all__ = [
    "MIN_PASSWORD_LENGTH",
    "hash_password",
    "verify_password",
]
