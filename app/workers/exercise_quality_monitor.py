import asyncio
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import ExerciseStatus
from app.db.db import async_session_maker
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)

logger = logging.getLogger(__name__)

QUALITY_MONITORING_INTERVAL_SECONDS = 60 * 60
MIN_WEIGHTED_ATTEMPTS_SUM_FOR_REVIEW = 7.0
EXERCISE_REVIEW_CANDIDATE_THRESHOLD = 0.4


async def check_exercises_for_review(session: AsyncSession):
    exercise_repo = SQLAlchemyExerciseRepository(session)

    min_weighted_attempts_sum = MIN_WEIGHTED_ATTEMPTS_SUM_FOR_REVIEW
    getter = exercise_repo.get_exercise_ids_for_quality_review
    exercise_ids_to_review = await getter(
        min_weighted_attempts_sum_for_review=min_weighted_attempts_sum,
        weighted_error_threshold=EXERCISE_REVIEW_CANDIDATE_THRESHOLD,
        default_user_rating=0.1,
    )

    if exercise_ids_to_review:
        updated_count = await exercise_repo.update_statuses(
            exercise_ids_to_review, ExerciseStatus.PENDING_REVIEW
        )
        logger.info(f'Moved {updated_count} exercises to PENDING_REVIEW.')
    else:
        logger.info(
            'No exercises met criteria for '
            'PENDING_REVIEW based on DB ratings.'
        )


async def quality_monitoring_worker_loop(stop_event: asyncio.Event):
    logger.info('Quality Monitoring Worker started.')

    while not stop_event.is_set():
        try:
            logger.info('Quality Monitoring Worker: Starting new cycle.')
            async with async_session_maker() as session:
                profile_repo = SQLAlchemyUserBotProfileRepository(session)
                await profile_repo.calc_and_store_ratings_for_profiles()
                await check_exercises_for_review(session)
                await session.commit()

            logger.info('Quality Monitoring Worker: Cycle finished.')

        except Exception as e:
            logger.error(
                f'Error in Quality Monitoring Worker cycle: {e}', exc_info=True
            )

        try:
            await asyncio.wait_for(
                stop_event.wait(), timeout=QUALITY_MONITORING_INTERVAL_SECONDS
            )
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            logger.info(
                'Quality Monitoring Worker loop task '
                'cancelled during sleep interval.'
            )
            break
    logger.info('Quality Monitoring Worker loop terminated.')
