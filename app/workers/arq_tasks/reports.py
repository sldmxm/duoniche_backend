import asyncio
import logging
from datetime import timedelta

from app.config import settings
from app.core.configs.enums import ReportStatus
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_report import UserReportService
from app.db.db import async_session_maker
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.db.repositories.user_report import SQLAlchemyUserReportRepository
from app.llm.llm_service import LLMService
from app.services.notification_producer import NotificationProducerService

logger = logging.getLogger(__name__)


async def _async_generate_detailed_report_task(
    report_id: int, llm_service: LLMService, arq_pool
) -> bool:
    async with async_session_maker() as session:
        report_repo = SQLAlchemyUserReportRepository(session)
        report = await report_repo.get_by_id(report_id)

        if not report or report.status != ReportStatus.PENDING:
            logger.warning(
                f"Skipping detailed report generation for report_id "
                f"{report_id}. "
                f"Report not found or status is not PENDING "
                f"(current: {report.status if report else 'N/A'})."
            )
            return False

        report.status = ReportStatus.GENERATING
        await report_repo.update(report)
        await session.commit()

        try:
            user_id = report.user_id
            bot_id = report.bot_id

            attempt_repo = SQLAlchemyExerciseAttemptRepository(session)
            user_bot_profile_service = UserBotProfileService(
                SQLAlchemyUserBotProfileRepository(session)
            )

            detailed_report_service = UserReportService(
                user_report_repository=report_repo,
                user_bot_profile_service=user_bot_profile_service,
                exercise_attempt_repository=attempt_repo,
                arq_pool=arq_pool,
                llm_service=llm_service,
            )

            full_report_text = await (
                detailed_report_service.generate_full_report_text(
                    user_id=user_id, bot_id=bot_id
                )
            )

            report.full_report = full_report_text
            report.status = ReportStatus.GENERATED
            await report_repo.update(report)
            await session.commit()

            logger.info(
                f'Generated detailed report for report_id {report.report_id}.'
            )
            return True

        except Exception as e:
            logger.error(
                f'Failed to generate detailed report for report_id '
                f'{report_id}: {e}',
                exc_info=True,
            )
            if report:
                report.status = ReportStatus.FAILED
                await report_repo.update(report)
                await session.commit()
            return False


async def send_detailed_report_notification_arq(ctx, report_id: int):
    """
    ARQ task to send the detailed report notification.
    This task is enqueued by generate_detailed_report_arq after a delay.
    """
    async with async_session_maker() as session:
        report_repo = SQLAlchemyUserReportRepository(session)
        report = await report_repo.get_by_id(report_id)

        if (
            not report
            or report.status != ReportStatus.GENERATED
            or not report.full_report
        ):
            logger.warning(
                f"Skipping full report notification for report_id {report_id}."
                f" Report not ready, status is not GENERATED, "
                f"or full_report is missing "
                f"(current status: {report.status if report else 'N/A'})."
            )
            return

        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get_by_id(report.user_id)
        profile_repo = SQLAlchemyUserBotProfileRepository(session)
        profile = await profile_repo.get(
            user_id=report.user_id, bot_id=report.bot_id
        )

        if not user or not profile:
            logger.error(
                f'User or profile not found for report_id {report_id}. '
                f'Cannot send full report notification.'
            )
            return

        notification_producer = NotificationProducerService()

        if await notification_producer.enqueue_detailed_report_notification(
            user=user, profile=profile, report=report
        ):
            report.status = ReportStatus.SENT
            await report_repo.update(report)
            await session.commit()
            logger.info(
                f'Full detailed report notification for report_id '
                f'"{report.report_id}" enqueued '
                f'and status updated to "SENT."'
            )
        else:
            logger.error(
                f'Failed to enqueue full detailed report notification '
                f'for report_id {report.report_id}.'
            )


async def generate_and_send_detailed_report_arq(ctx, report_id: int):
    """
    ARQ task to generate a detailed report and then enqueue a separate task
    to send it after a delay.
    """
    logger.info(f'Starting ARQ task for detailed report_id: {report_id}')

    llm_service = ctx.get('llm_service')
    arq_pool = ctx.get('arq_pool')

    if not llm_service or not arq_pool:
        logger.error(
            'LLMService or arq_pool not found in ARQ context. '
            'Check on_startup hook.'
        )
        return

    generation_successful = await _async_generate_detailed_report_task(
        report_id, llm_service=llm_service, arq_pool=arq_pool
    )

    if generation_successful:
        arq_pool = ctx.get('arq_pool') or ctx.get('redis')
        if not arq_pool:
            logger.error(
                'Could not find arq_pool or redis in ARQ context '
                'to enqueue job.'
            )
            return

        delay = settings.full_weekly_report_sending_delay

        logger.info(
            f'Report for report_id {report_id} generated. '
            f'Enqueuing notification send task with a delay of '
            f'{delay}s.'
        )
        await arq_pool.enqueue_job(
            'send_detailed_report_notification_arq',
            report_id,
            _defer_by=timedelta(seconds=delay),
        )
    else:
        logger.info(
            f'Report generation for report_id {report_id} was not '
            f'successful or skipped. Notification not sent by this task.'
        )


async def run_report_generation_cycle_arq(ctx):
    """
    ARQ task to generate short weekly reports for active users, save them,
    and enqueue notifications in throttled batches.
    This task is scheduled to run on Mondays via cron.
    """
    logger.info('Starting ARQ task for weekly report generation cycle.')

    async with async_session_maker() as session:
        user_profile_repo = SQLAlchemyUserBotProfileRepository(session)
        attempt_repo = SQLAlchemyExerciseAttemptRepository(session)
        report_repo = SQLAlchemyUserReportRepository(session)

        user_bot_profile_service = UserBotProfileService(
            profile_repo=user_profile_repo
        )

        arq_pool = ctx.get('arq_pool') or ctx.get('redis')
        llm_service = ctx.get('llm_service')

        if not arq_pool or not llm_service:
            logger.error(
                'arq_pool or llm_service not found in ARQ context. '
                'Check on_startup hook.'
            )
            return

        report_service = UserReportService(
            user_report_repository=report_repo,
            exercise_attempt_repository=attempt_repo,
            user_bot_profile_service=user_bot_profile_service,
            arq_pool=arq_pool,
            llm_service=llm_service,
        )

        reports_to_notify = await (
            report_service.generate_and_save_short_weekly_reports()
        )

        await session.commit()

    if not reports_to_notify:
        logger.info('No reports were generated, finishing task.')
        return

    notification_producer = NotificationProducerService()

    batch_size = settings.report_notification_batch_size
    delay = settings.report_notification_batch_delay_seconds

    for i in range(0, len(reports_to_notify), batch_size):
        batch = reports_to_notify[i : i + batch_size]
        for profile, user, report in batch:
            if not user:
                logger.warning(
                    f'Profile {profile.user_id}/{profile.bot_id} '
                    'is missing user data. Skipping notification.'
                )
                continue
            await notification_producer.enqueue_weekly_report_notification(
                user=user, profile=profile, report=report
            )
        if i + batch_size < len(reports_to_notify):
            logger.info(f'Waiting for {delay} seconds before next batch.')
            await asyncio.sleep(delay)
