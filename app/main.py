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
from app.services.file_storage_service import R2FileStorageService
from app.services.notification_producer import NotificationProducerService
from app.services.tts_service import GoogleTTSService
from app.workers.exercise_quality_monitor import quality_monitoring_worker_loop
from app.workers.exercise_review_processor import (
    exercise_review_processor_loop,
)
from app.workers.exercise_stock_refill import exercise_stock_refill_loop
from app.workers.metrics_updater import metrics_loop
from app.workers.notification_scheduler import notification_scheduler_loop

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
    app.state.file_storage_service = R2FileStorageService()
    app.state.tts_service = GoogleTTSService()
    app.state.llm_service = LLMService()
    app.state.translator = LLMTranslator()
    app.state.choose_accent_generator = ChooseAccentGenerator(
        http_client=app.state.http_client
    )
    app.state.producer = NotificationProducerService()

    stop_event = asyncio.Event()

    metrics_task = asyncio.create_task(
        metrics_loop(
            stop_event=stop_event,
        ),
        name='metrics_loop',
    )
    exercise_refill_task = asyncio.create_task(
        exercise_stock_refill_loop(
            llm_service=app.state.llm_service,
            choose_accent_generator=app.state.choose_accent_generator,
            tts_service=app.state.tts_service,
            file_storage_service=app.state.file_storage_service,
            http_client=app.state.http_client,
            stop_event=stop_event,
        ),
        name='exercise_refill_loop',
    )
    notification_scheduler_task = asyncio.create_task(
        notification_scheduler_loop(
            notification_producer=app.state.producer,
            stop_event=stop_event,
        ),
        name='notification_scheduler_loop',
    )
    quality_monitoring_worker_task = asyncio.create_task(
        quality_monitoring_worker_loop(stop_event=stop_event)
    )
    exercise_review_processor_worker_task = asyncio.create_task(
        exercise_review_processor_loop(stop_event=stop_event)
    )

    logger.info('Application startup complete. All workers started.')
    yield

    logger.info('Application shutdown initiated.')
    worker_tasks = [
        metrics_task,
        exercise_refill_task,
        notification_scheduler_task,
        quality_monitoring_worker_task,
        exercise_review_processor_worker_task,
    ]
    stop_event.set()
    for task in worker_tasks:
        if not task.done():
            try:
                await asyncio.wait_for(
                    task, timeout=settings.worker_shutdown_timeout_seconds
                )
                logger.info(
                    f'Worker task {task.get_name()} finished gracefully.'
                )
            except asyncio.TimeoutError:
                logger.warning(
                    f'Worker task {task.get_name()} timed '
                    f'out during shutdown. Cancelling.'
                )
                task.cancel()
            except asyncio.CancelledError:
                logger.info(
                    f'Worker task {task.get_name()} was '
                    f'cancelled during shutdown.'
                )
            except Exception as e:
                logger.error(
                    f'Error during shutdown of worker task '
                    f'{task.get_name()}: {e}',
                    exc_info=True,
                )

    if hasattr(app.state, 'http_client') and app.state.http_client:
        await app.state.http_client.aclose()
    if hasattr(app.state, 'async_task_cache') and app.state.async_task_cache:
        app.state.async_task_cache.clear()
    if hasattr(app.state, 'tts_service') and app.state.tts_service:
        await app.state.tts_service.close_rest_http_client()

    await close_redis_client()

    logger.info('Application shutdown complete.')


app = FastAPI(title='DuoNiche API', lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix='/api/v1')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app.main:app', reload=True)
