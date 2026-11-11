from __future__ import annotations

import argparse
import asyncio
from getpass import getpass

from src.core.auth.service import AuthService
from src.core.config import get_settings
from src.core.exceptions import InvalidInput
from src.db.session import create_engine, create_session_factory, session_scope


async def _set_password(email: str, password: str) -> None:
    settings = get_settings()
    engine = create_engine(settings.database)
    try:
        async for session in session_scope(create_session_factory(engine)):
            service = AuthService(session, settings.auth)
            await service.set_password(email, password)
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="ops-api-auth")
    commands = parser.add_subparsers(dest="command", required=True)
    set_password = commands.add_parser("set-password", help="Set or replace a password")
    set_password.add_argument("email")
    args = parser.parse_args(argv)

    password = getpass("New password: ")
    if getpass("Repeat it: ") != password:
        parser.exit(1, "The passwords do not match\n")
    try:
        asyncio.run(_set_password(args.email, password))
    except InvalidInput as error:
        parser.exit(1, f"{error.message}\n")
    print(f"Password set for {args.email}")


if __name__ == "__main__":
    main()
