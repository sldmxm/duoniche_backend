from typing import Any, AsyncGenerator

import asyncpg
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.models.base import Base


async def create_clean_test_db():
    """Create a clean test database."""
    sys_conn = await asyncpg.connect(
        database='postgres',
        user=settings.postgres_user,
        password=settings.postgres_password,
        host=settings.postgres_host,
        port=int(settings.postgres_port),
    )

    try:
        db_exists = await sys_conn.fetchval(
            'SELECT 1 FROM pg_database WHERE datname = $1',
            settings.postgres_db,
        )
        if db_exists:
            await sys_conn.execute(
                f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{settings.postgres_db}'
                AND pid <> pg_backend_pid()
                """
            )
            await sys_conn.execute(f'DROP DATABASE {settings.postgres_db}')

        await sys_conn.execute(f'CREATE DATABASE {settings.postgres_db}')
    finally:
        await sys_conn.close()


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_test_database():
    """Setup test database and create tables."""
    await create_clean_test_db()
    engine = create_async_engine(settings.test_database_url, echo=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def engine() -> AsyncGenerator[AsyncEngine, Any]:
    engine = create_async_engine(
        settings.test_database_url,
        echo=False,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(engine) -> AsyncGenerator[AsyncSession, Any]:
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
