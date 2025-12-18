"""Pytest configuration and fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

from app.main import app
from app.core.database import get_session
from app.core.security import get_password_hash
from app.models import User, UserRole


# Test database URL (in-memory SQLite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(test_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with overridden dependencies."""

    async def override_get_session():
        yield test_session

    app.dependency_overrides[get_session] = override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def admin_user(test_session) -> User:
    """Create admin user for testing."""
    user = User(
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin User",
        role=UserRole.ADMIN,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def author_user(test_session) -> User:
    """Create author user for testing."""
    user = User(
        email="author@test.com",
        hashed_password=get_password_hash("author123"),
        full_name="Author User",
        role=UserRole.AUTHOR,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def reviewer_user(test_session) -> User:
    """Create reviewer user for testing."""
    user = User(
        email="reviewer@test.com",
        hashed_password=get_password_hash("reviewer123"),
        full_name="Reviewer User",
        role=UserRole.REVIEWER,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_token(client, admin_user) -> str:
    """Get admin authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "admin@test.com", "password": "admin123"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def author_token(client, author_user) -> str:
    """Get author authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "author@test.com", "password": "author123"},
    )
    return response.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def reviewer_token(client, reviewer_user) -> str:
    """Get reviewer authentication token."""
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "reviewer@test.com", "password": "reviewer123"},
    )
    return response.json()["access_token"]


def auth_headers(token: str) -> dict:
    """Create authorization headers."""
    return {"Authorization": f"Bearer {token}"}
