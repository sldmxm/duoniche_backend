import asyncio
import logging
from datetime import datetime, timedelta, timezone

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

logger = logging.getLogger(__name__)

REPORT_GENERATION_INTERVAL_SECONDS = 60 * 60 * 24 * 7
MIN_ATTEMPTS_FOR_REPORT = 5


async def run_report_generation_cycle():
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

        for profile in active_profiles:
            current_summary = (
                await attempt_repo.get_period_summary_for_user_and_bot(
                    user_id=profile.user_id,
                    bot_id=profile.bot_id.value,
                    start_date=start_date_current,
                    end_date=end_date_current,
                )
            )

            logger.info(f'Current summary: {current_summary}')

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
                language_code=profile.bot_id.name.lower(),
                user_language=profile.user_language,
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

                logger.info(
                    f'Successfully generated and saved report for user '
                    f'{profile.user_id}/{profile.bot_id.value}'
                )
            except Exception as e:
                logger.error(
                    f'Failed to generate or save report for user '
                    f'{profile.user_id}/{profile.bot_id.value}. Error: {e}',
                    exc_info=True,
                )

        await session.commit()


async def report_generator_worker_loop(stop_event: asyncio.Event):
    logger.info('Report Generator Worker started.')
    while not stop_event.is_set():
        try:
            logger.info('Report Generator Worker: Starting new cycle.')
            await run_report_generation_cycle()
            logger.info('Report Generator Worker: Cycle finished.')
        except Exception as e:
            logger.error(
                f'Error in Report Generator Worker cycle: {e}',
                exc_info=True,
            )

        try:
            await asyncio.wait_for(
                stop_event.wait(),
                timeout=REPORT_GENERATION_INTERVAL_SECONDS,
            )
            if stop_event.is_set():
                break
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            logger.info(
                'Report Generator Worker loop task cancelled '
                'during sleep interval.',
            )
            break
    logger.info('Report Generator Worker loop terminated.')
