from collections.abc import AsyncGenerator
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

from src.admin.models import SystemSettingsBase
from src.auth.service import create_access_token
from src.config import settings
from src.database import Base, get_async_session
from src.main import app
from src.users.models import User
from src.users.schemas import UserCreate
from src.users.service import create_user
from tests import utils


@pytest.fixture(scope="session")
async def _engine() -> AsyncGenerator[AsyncEngine]:
    """Module-scoped engine."""
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(SystemSettingsBase.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
async def _connection(_engine: AsyncEngine) -> AsyncGenerator[AsyncConnection]:
    """Module-scoped connection with outer transaction that rolls back after all tests."""
    async with _engine.connect() as connection, connection.begin() as transaction:
        yield connection
        await transaction.rollback()


@pytest.fixture(scope="session")
async def _base_session(_connection: AsyncConnection) -> AsyncGenerator[AsyncSession]:
    """Module-scoped session for creating shared test data."""
    session = AsyncSession(bind=_connection, expire_on_commit=False)
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture(scope="session")
async def _async_client() -> AsyncGenerator[AsyncClient]:
    """Session-scoped HTTP client (reused across tests)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def session(_connection: AsyncConnection) -> AsyncGenerator[AsyncSession]:
    """Function-scoped session with savepoint that rolls back after each test."""
    async with _connection.begin_nested():
        session = AsyncSession(bind=_connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
async def client(
    session: AsyncSession, _async_client: AsyncClient
) -> AsyncGenerator[AsyncClient]:
    """Function-scoped client without authentication."""
    app.dependency_overrides[get_async_session] = lambda: session
    _async_client.headers.pop("Authorization", None)
    _async_client.cookies.clear()
    yield _async_client
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(
    client: AsyncClient, valid_access_token: str
) -> AsyncClient:
    """Client with valid authentication header."""
    client.headers["Authorization"] = f"Bearer {valid_access_token}"
    return client


@pytest.fixture
async def expired_token_client(
    client: AsyncClient, expired_access_token: str
) -> AsyncClient:
    """Client with expired authentication header."""
    client.headers["Authorization"] = f"Bearer {expired_access_token}"
    return client


@pytest.fixture(scope="session")
async def test_user(_base_session: AsyncSession) -> User:
    """Session-scoped test user created once for all tests."""
    return await create_user(
        _base_session,
        UserCreate(
            email=utils.TEST_USER_EMAIL,
            username=utils.TEST_USER_USERNAME,
            password=utils.TEST_USER_PASSWORD,
        ),
    )


@pytest.fixture(scope="session")
async def test_user2(_base_session: AsyncSession) -> User:
    """Session-scoped test user created once for all tests."""
    return await create_user(
        _base_session,
        UserCreate(
            email=utils.TEST_USER2_EMAIL,
            username=utils.TEST_USER2_USERNAME,
            password=utils.TEST_USER2_PASSWORD,
        ),
    )


@pytest.fixture(scope="session")
async def expired_access_token(test_user: User) -> str:
    """Session-scoped expired access token for the test user."""
    return create_access_token(
        test_user.id,
        expires_delta=-timedelta(minutes=1),
    )


@pytest.fixture(scope="session")
async def valid_access_token(test_user: User) -> str:
    """Session-scoped valid access token for the test user."""
    return create_access_token(test_user.id)
