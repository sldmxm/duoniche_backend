from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.db.models.base import Base

engine = create_async_engine(settings.database_url, echo=True)


async def init_models(engine: AsyncEngine = engine) -> None:
    """Initialize models."""
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
    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session
