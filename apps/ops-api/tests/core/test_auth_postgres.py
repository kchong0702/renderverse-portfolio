from uuid import uuid4

from sqlalchemy import delete

from src.core.auth.models import SignInAttempts
from src.core.auth.service import AuthService
from src.core.config import AuthSettings
from src.core.exceptions import ServiceException
from src.db.session import create_session_factory
from tests.core.conftest import needs_postgres

pytestmark = needs_postgres


async def test_password_sign_ins_are_limited_on_postgres(engine):
    factory = create_session_factory(engine)
    email = f"{uuid4()}@example.com"
    address = str(uuid4())
    statuses = []
    try:
        for _ in range(6):
            async with factory() as session:
                try:
                    await AuthService(session, AuthSettings()).sign_in_with_password(
                        email, "wrong password", address
                    )
                except ServiceException as error:
                    statuses.append(error.status_code)
    finally:
        async with factory() as session, session.begin():
            await session.execute(
                delete(SignInAttempts).where(SignInAttempts.value.in_([email, address]))
            )

    assert statuses == [401] * 5 + [429]
