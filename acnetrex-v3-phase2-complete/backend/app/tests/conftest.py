"""
Test fixtures. These tests are integration tests against a real Postgres
database (with pgvector installed) - point DATABASE_URL at a disposable test
database before running, e.g.:

    createdb acnetrex_test
    DATABASE_URL=postgresql+asyncpg://acnetrex:acnetrex@localhost:5432/acnetrex_test alembic upgrade head
    DATABASE_URL=postgresql+asyncpg://acnetrex:acnetrex@localhost:5432/acnetrex_test pytest

Each test runs inside a transaction that's rolled back afterward, so the
database is left clean regardless of test outcome.
"""
import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal, engine
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await engine.dispose()
