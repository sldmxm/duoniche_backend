import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.api import api_router
from app.config import settings
from app.core.services.async_task_cache import AsyncTaskCache
from app.db.db import init_db
from app.infrastructure.redis_client import (
    close_redis_client,
    get_redis_client,
)
from app.llm.llm_service import LLMService
from app.llm.llm_translator import LLMTranslator
from app.logging_config import configure_logging
from app.sentry_sdk import sentry_init
from app.services.choose_accent_generator import ChooseAccentGenerator
from app.workers.exercise_stock_refill import exercise_stock_refill_loop
from app.workers.metrics_updater import metrics_loop

configure_logging()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    if not settings.debug:
        sentry_init()

    await init_db()

    app.state.http_client = httpx.AsyncClient()
    app.state.redis_client = await get_redis_client()
    app.state.async_task_cache = AsyncTaskCache(app.state.redis_client)
    app.state.async_task_cache.clear()
    app.state.llm_service = LLMService()
    app.state.translator = LLMTranslator()
    app.state.choose_accent_generator = ChooseAccentGenerator(
        http_client=app.state.http_client
    )

    metrics_task = asyncio.create_task(metrics_loop())
    exercise_refill_task = asyncio.create_task(
        exercise_stock_refill_loop(
            llm_service=app.state.llm_service,
            choose_accent_generator=app.state.choose_accent_generator,
        )
    )
    logger.info('Application startup complete.')
    yield

    logger.info('Application shutdown initiated.')
    if not metrics_task.done():
        metrics_task.cancel()
    if not exercise_refill_task.done():
        exercise_refill_task.cancel()
    # TODO: Закрыть вокер уведомлений
    try:
        await metrics_task
    except asyncio.CancelledError:
        logger.info('Metrics loop cancelled.')
    try:
        await exercise_refill_task
    except asyncio.CancelledError:
        logger.info('Exercise refill loop cancelled.')
    if hasattr(app.state, 'http_client') and app.state.http_client:
        await app.state.http_client.aclose()
    if hasattr(app.state, 'async_task_cache') and app.state.async_task_cache:
        app.state.async_task_cache.clear()
    await close_redis_client()
    logger.info('Application shutdown complete.')


app = FastAPI(title='DuoNiche API', lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix='/api/v1')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app.main:app', reload=True)
