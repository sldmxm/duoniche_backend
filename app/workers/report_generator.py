import asyncio
import logging
from datetime import datetime, timedelta, timezone

from asgiref.sync import async_to_sync

from app.celery_producer import notifier_celery_producer as celery_app
from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import UserBotProfile
from app.core.entities.user_report import UserReport
from app.core.texts import Messages, get_text
from app.db.db import async_session_maker
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.db.repositories.user_report import SQLAlchemyUserReportRepository
from app.services.notification_producer import NotificationProducerService

logger = logging.getLogger(__name__)

MIN_ATTEMPTS_FOR_REPORT = 15


async def _async_run_report_generation_cycle():
    """
    Generates short weekly reports for active users, saves them,
    and enqueues notifications in throttled batches.
    This task is scheduled to run on Mondays.
    """
    # if datetime.now(timezone.utc).weekday() != 0:
    #     logger.info('Not Monday, skipping weekly report generation.')
    #     return

    end_date_current = datetime.now(timezone.utc)
    start_date_current = end_date_current - timedelta(days=7)
    week_start_date_current = start_date_current.date()
    async with async_session_maker() as session:
        user_profile_repo = SQLAlchemyUserBotProfileRepository(session)
        attempt_repo = SQLAlchemyExerciseAttemptRepository(session)
        report_repo = SQLAlchemyUserReportRepository(session)

        active_profiles = (
            await user_profile_repo.get_active_profiles_for_reporting(
                since=start_date_current,
            )
        )

        logger.info(
            f'Found {len(active_profiles)} active users for weekly report '
            'generation.'
        )

        reports_to_notify: list[tuple[UserBotProfile, User, UserReport]] = []
        for profile, user in active_profiles:
            current_summary = (
                await attempt_repo.get_period_summary_for_user_and_bot(
                    user_id=profile.user_id,
                    bot_id=profile.bot_id.value,
                    start_date=start_date_current,
                    end_date=end_date_current,
                )
            )

            if (
                not current_summary
                or current_summary.get('total_attempts', 0)
                < MIN_ATTEMPTS_FOR_REPORT
            ):
                logger.info(
                    f'Skipping report for user {profile.user_id}/'
                    f'{profile.bot_id.value} due to low activity.'
                )
                continue

            total_attempts = current_summary.get('total_attempts', 0)
            correct_attempts = current_summary.get('correct_attempts', 0)
            accuracy = (
                (correct_attempts / total_attempts) * 100
                if total_attempts > 0
                else 0
            )
            active_days = current_summary.get('active_days', 0)

            short_report_text = get_text(
                Messages.WEEKLY_REPORT,
                language_code=profile.user_language,
                active_days=active_days,
                total_attempts=total_attempts,
                accuracy=accuracy,
            )

            try:
                new_report = UserReport(
                    user_id=profile.user_id,
                    bot_id=profile.bot_id.value,
                    week_start_date=week_start_date_current,
                    short_report=short_report_text,
                    full_report=None,
                    generated_at=datetime.now(timezone.utc),
                )

                saved_report = await report_repo.create(new_report)
                profile.last_report_generated_at = saved_report.generated_at
                await user_profile_repo.update(profile)

                reports_to_notify.append((profile, user, saved_report))

                logger.info(
                    f'Successfully generated and saved report for user '
                    f'{profile.user_id}/{profile.bot_id.value} '
                    f'(report_id: {saved_report.report_id})'
                )
            except Exception as e:
                logger.error(
                    f'Failed to generate or save report for user '
                    f'{profile.user_id}/{profile.bot_id.value}. Error: {e}',
                    exc_info=True,
                )

        await session.commit()

    notification_producer = NotificationProducerService()
    batch_size = settings.report_notification_batch_size
    delay = settings.report_notification_batch_delay_seconds

    for i in range(0, len(reports_to_notify), batch_size):
        batch = reports_to_notify[i : i + batch_size]
        for profile, user, report in batch:
            if not user:
                logger.warning(
                    f'Profile {profile.user_id}/{profile.bot_id.value} '
                    'is missing user data. Skipping notification.'
                )
                continue
            await notification_producer.enqueue_weekly_report_notification(
                user=user, profile=profile, report=report
            )
        if i + batch_size < len(reports_to_notify):
            await asyncio.sleep(delay)


@celery_app.task(name='report_generator.run_report_generation_cycle')
def run_report_generation_cycle():
    """
    Synchronous wrapper for the Celery task that runs the async logic.
    """
    logger.info(
        "Synchronous Celery task 'run_report_generation_cycle' started."
    )
    try:
        async_to_sync(_async_run_report_generation_cycle)()
        logger.info(
            "Asynchronous part of 'run_report_generation_cycle' completed."
        )
    except Exception as e:
        logger.error(
            f"Error in 'run_report_generation_cycle': {e}", exc_info=True
        )
