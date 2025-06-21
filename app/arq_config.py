import logging

import httpx
from arq import cron
from arq.connections import RedisSettings

from app.config import settings
from app.llm.llm_service import LLMService
from app.workers.arq_tasks.reports import (
    generate_and_send_detailed_report_arq,
    run_report_generation_cycle_arq,
    send_detailed_report_notification_arq,
)

logger = logging.getLogger(__name__)


async def startup(ctx):
    """
    Выполняется один раз при старте воркера.
    Создаем здесь все необходимые зависимости.
    """
    logger.info('ARQ worker starting up...')
    http_client = httpx.AsyncClient()
    ctx['http_client'] = http_client
    ctx['llm_service'] = LLMService(http_client=http_client)
    ctx['arq_pool'] = ctx['redis']

    logger.info('ARQ worker started successfully with all dependencies.')


async def shutdown(ctx):
    """
    Выполняется один раз при остановке воркера.
    Закрываем здесь все открытые ресурсы.
    """
    logger.info('ARQ worker shutting down...')
    http_client: httpx.AsyncClient = ctx.get('http_client')
    if http_client:
        await http_client.aclose()
    logger.info('ARQ worker shut down successfully.')


class WorkerSettings:
    """
    Defines the configuration for the ARQ worker.
    This class is referenced by the ARQ CLI.
    """

    redis_settings = RedisSettings.from_dsn(settings.redis_url)

    functions = [
        generate_and_send_detailed_report_arq,
        send_detailed_report_notification_arq,
        run_report_generation_cycle_arq,
    ]
    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [
        cron(
            run_report_generation_cycle_arq,
            hour=9,
            minute=0,
            weekday='mon',
            run_at_startup=False,
        )
    ]
