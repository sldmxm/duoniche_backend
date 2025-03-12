import contextlib

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.db import drop_models, get_async_session, init_db

pytestmark = pytest.mark.asyncio


async def test_get_async_session(async_session: AsyncSession):
    assert async_session
    async with async_session.begin():
        result = await async_session.execute(text('SELECT 1'))
        assert result.scalar() == 1


async def test_session_rollback(async_session: AsyncSession):
    """Test session rollback."""
    async with async_session as session:
        async with session.begin():
            result = await session.execute(text('SELECT 1'))
            assert result.scalar() == 1

        with contextlib.suppress(Exception):
            async with session.begin():
                await session.execute(text('SELECT invalid_column'))

        async with session.begin():
            result = await session.execute(text('SELECT 1'))
            assert result.scalar() == 1


async def test_init_and_drop_models(engine):
    """Test init_models and drop_models functions."""
    async with engine.begin() as conn:
        # Test init_models
        await init_db(engine)
        result = await conn.execute(
            text(
                'SELECT EXISTS ('
                'SELECT FROM information_schema.tables '
                "WHERE table_name = 'exercises')"
            )
        )
        assert result.scalar() is True

    async with engine.begin() as conn:
        # Test drop_models
        await drop_models(engine)
        result = await conn.execute(
            text(
                'SELECT EXISTS ('
                'SELECT FROM information_schema.tables'
                " WHERE table_name = 'exercises')"
            )
        )
        assert result.scalar() is False


async def test_get_async_session_context(engine):
    """Test the get_async_session function with context manager."""
    async with engine.begin() as _:
        async for session_from_generator in get_async_session(engine):
            assert session_from_generator is not None
            async with session_from_generator.begin():
                result = await session_from_generator.execute(text('SELECT 1'))
                assert result.scalar() == 1


async def test_init_models_when_tables_exists(engine):
    """Test init_models when tables exists."""
    async with engine.begin() as conn:
        # Create tables first
        await init_db(engine)

        # Try to create tables again
        await init_db(engine)

        result = await conn.execute(
            text(
                'SELECT EXISTS ('
                'SELECT FROM information_schema.tables '
                "WHERE table_name = 'exercises')"
            )
        )
        assert result.scalar() is True


async def test_drop_models_when_tables_not_exists(engine):
    """Test drop_models when tables not exists."""
    async with engine.begin() as conn:
        # Drop tables first
        await drop_models(engine)

        # Try to drop tables again
        await drop_models(engine)

        result = await conn.execute(
            text(
                'SELECT EXISTS ('
                'SELECT FROM information_schema.tables'
                " WHERE table_name = 'exercises')"
            )
        )
        assert result.scalar() is False
