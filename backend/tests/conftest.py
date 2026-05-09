"""
Test configuration and shared fixtures.

Requires a running PostgreSQL instance. Set TEST_DATABASE_URL env var or it
defaults to postgres://postgres:postgres@localhost:5432/book_manager_test.

Run with:
  cd backend
  pytest tests/ -v
"""

from __future__ import annotations

import asyncio
import os
import uuid
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token
from app.db.models import User
from app.db.session import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/book_manager_test",
)

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    """Create all tables once at session start, drop at end."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional test session that rolls back after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await conn.rollback()


async def override_get_db(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    yield session


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient wired to the FastAPI app with the test DB session."""
    app.dependency_overrides[get_db] = lambda: override_get_db(db_session)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# User factory helpers
# ---------------------------------------------------------------------------

def make_user(**kwargs) -> User:
    defaults = dict(
        google_sub=f"google-sub-{uuid.uuid4().hex[:8]}",
        email=f"test-{uuid.uuid4().hex[:6]}@example.com",
        name="Test User",
        phone_number="+84900000001",
        phone_verified=True,
    )
    defaults.update(kwargs)
    return User(**defaults)


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def user_a(db_session: AsyncSession) -> User:
    u = make_user(name="Alice", email="alice@example.com")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


@pytest_asyncio.fixture
async def user_b(db_session: AsyncSession) -> User:
    u = make_user(name="Bob", email="bob@example.com", phone_number="+84900000002")
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u
