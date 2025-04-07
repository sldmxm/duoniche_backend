import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.v1.api import api_router
from app.db.db import init_db
from app.logging_config import configure_logging
from app.metrics import metrics_loop

configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, Any]:
    await init_db()
    asyncio.create_task(metrics_loop())
    yield


app = FastAPI(title='Learn BG API', lifespan=lifespan)

Instrumentator().instrument(app).expose(app)

app.include_router(api_router, prefix='/api/v1')


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app.main:app', reload=True)
