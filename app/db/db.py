from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings
from app.db.base import Base

engine = create_async_engine(settings.database_url, echo=False)


async def init_db(engine: AsyncEngine = engine) -> None:
    """Initialize db."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_models(engine: AsyncEngine = engine) -> None:
    """Drop models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def get_async_session(
    engine: AsyncEngine = engine,
) -> AsyncGenerator[AsyncSession, None]:
    """Get async session."""
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
