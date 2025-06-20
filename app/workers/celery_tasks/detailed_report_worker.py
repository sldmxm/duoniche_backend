import asyncio
import logging

from app.celery_producer import notifier_celery_producer
from app.core.entities.user_bot_profile import BotID
from app.core.enums import ReportStatus
from app.core.services.detailed_report import DetailedReportService
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

FULL_REPORT_SENDING_DELAY = 3  # * 10 * 60  # TODO: поставить норм


async def _async_generate_detailed_report_task(report_id) -> bool:
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
            bot_id = BotID(report.bot_id)

            llm_service = LLMService(http_client=None)  # type: ignore
            attempt_repo = SQLAlchemyExerciseAttemptRepository(session)
            profile_repo = SQLAlchemyUserBotProfileRepository(session)

            detailed_report_service = DetailedReportService(
                user_report_repository=report_repo,
                exercise_attempt_repository=attempt_repo,
                llm_service=llm_service,
            )

            profile = await profile_repo.get(user_id=user_id, bot_id=bot_id)

            if not profile:
                logger.error(f'Profile not found for user_id {user_id} ')
                return False

            full_report_text = await (
                detailed_report_service.generate_full_report_text(profile)
            )

            report.full_report = full_report_text
            report.status = ReportStatus.GENERATED
            await report_repo.update(report)
            await session.commit()

            logger.info(
                f'Enqueued notification task for report_id '
                f'{report.report_id} with delay '
                f'{FULL_REPORT_SENDING_DELAY}s.'
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


async def _async_send_report_notification_task(report_id):
    async with async_session_maker() as session:
        report_repo = SQLAlchemyUserReportRepository(session)
        report = await report_repo.get_by_id(report_id)

        if (
            not report
            or report.status != ReportStatus.GENERATED
            or not report.full_report
        ):
            logger.warning(
                f"Skipping full report notification "
                f"for report_id {report_id}. "
                f"Report not ready, status is not GENERATED, "
                f"or full_report is missing "
                f"(current status: {report.status if report else 'N/A'})."
            )
            return

        user_repo = SQLAlchemyUserRepository(session)
        user = await user_repo.get_by_id(report.user_id)
        profile_repo = SQLAlchemyUserBotProfileRepository(session)
        profile = await profile_repo.get(
            user_id=report.user_id, bot_id=BotID(report.bot_id)
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
                f'"{report.report_id} enqueued '
                f'and status updated to "SENT."'
            )
        else:
            logger.error(
                f'Failed to enqueue full detailed report notification '
                f'for report_id {report.report_id}.'
            )


async def _async_generate_and_send_detailed_report(report_id: int):
    generation_successful = await _async_generate_detailed_report_task(
        report_id
    )
    if generation_successful:
        await asyncio.sleep(FULL_REPORT_SENDING_DELAY)
        await _async_send_report_notification_task(report_id)
    else:
        logger.info(
            f'Report generation for report_id {report_id} was not successful '
            f'or skipped. Notification will not be sent by this task.'
        )


@notifier_celery_producer.task(
    name='detailed_report.generate_and_send_detailed_report_task',
)
def generate_and_send_detailed_report(report_id: int):
    """Celery task to generate a detailed report and then send it."""
    logger.info(f'Starting async task for detailed report_id: {report_id}')
    try:
        # This ensures a clean, isolated event loop for each task run.
        asyncio.run(_async_generate_and_send_detailed_report(report_id))
        logger.info(f'Finished async task for detailed report_id: {report_id}')
    except Exception as e:
        logger.error(
            f'Error in async task for detailed report_id {report_id}: {e}',
            exc_info=True,
        )
        # Re-raise to mark task as FAILED.
        raise
