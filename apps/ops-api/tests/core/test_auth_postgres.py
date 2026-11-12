import asyncio
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete

from src.core.auth.enums import IdentityProvider
from src.core.auth.models import AuthIdentity, SignInAttempts, User
from src.core.auth.service import AuthService
from src.core.config import AuthSettings
from src.core.exceptions import Conflict, ServiceException
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


async def test_parallel_unlinks_keep_the_last_method(engine, postgres_user: UUID):
    factory = create_session_factory(engine)
    async with factory() as session, session.begin():
        session.add_all(
            [
                AuthIdentity(
                    user_id=postgres_user,
                    provider=IdentityProvider.PASSWORD,
                    email=f"{postgres_user}@example.com",
                    secret_hash="hash",
                ),
                AuthIdentity(
                    user_id=postgres_user,
                    provider=IdentityProvider.GOOGLE,
                    subject=str(postgres_user),
                    email=f"{postgres_user}@example.com",
                ),
            ]
        )
    user = User(id=postgres_user)

    async with factory() as first, factory() as second:
        await AuthService(first, AuthSettings()).unlink(user, IdentityProvider.GOOGLE)
        racing = asyncio.create_task(
            AuthService(second, AuthSettings()).unlink(user, IdentityProvider.PASSWORD)
        )
        await asyncio.sleep(0.5)
        assert not racing.done()
        await first.commit()
        with pytest.raises(Conflict):
            await racing
