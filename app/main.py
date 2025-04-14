import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.api import api_router
from app.config import settings
from app.db.db import init_db
from app.logging_config import configure_logging
from app.metrics import metrics_loop
from app.sentry_sdk import sentry_init
from app.utils.exercise_refill import exercise_refill_loop

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    await init_db()
    if not settings.debug:
        sentry_init()
    asyncio.create_task(metrics_loop())
    asyncio.create_task(exercise_refill_loop())
    yield


app = FastAPI(title='DuoNiche API', lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix='/api/v1')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app.main:app', reload=True)
