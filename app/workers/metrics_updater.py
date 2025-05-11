import asyncio
import collections
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Set

from app.db.db import async_session_maker
from app.db.models import DBUserBotProfile
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.metrics import BACKEND_USER_METRICS, backend_user_metrics_label_names

logger = logging.getLogger(__name__)

UPDATE_USER_METRICS_INTERVAL = 60
SESSION_TTL_SINCE_LAST_EXERCISE = timedelta(minutes=5)

all_possible_active_user_labels: Set[tuple] = set()


async def update_user_sessions_metrics():
    now = datetime.now(timezone.utc)
    active_users_label_counts = collections.Counter()
    try:
        async with async_session_maker() as session:
            user_profile_repo = SQLAlchemyUserBotProfileRepository(session)
            period_seconds = int(
                SESSION_TTL_SINCE_LAST_EXERCISE.total_seconds()
                + UPDATE_USER_METRICS_INTERVAL
            )
            profiles: List[
                DBUserBotProfile
            ] = await user_profile_repo.get_by_recent_exercise_with_user_data(
                period_seconds=period_seconds
            )

            for profile in profiles:
                label_tuple = (
                    profile.user.cohort,
                    profile.user.plan,
                    profile.bot_id.value,
                    profile.user_language,
                    profile.language_level.value,
                )

                label_dict = dict(
                    zip(
                        backend_user_metrics_label_names,
                        label_tuple,
                        strict=False,
                    )
                )
                all_possible_active_user_labels.add(label_tuple)

                if (
                    profile.session_frozen_until is not None
                    or now - profile.last_exercise_at
                    > SESSION_TTL_SINCE_LAST_EXERCISE
                ):
                    session_duration = (
                        profile.last_exercise_at - profile.session_started_at
                    ).total_seconds()
                    BACKEND_USER_METRICS['session_length'].labels(
                        **label_dict
                    ).observe(session_duration)
                    BACKEND_USER_METRICS['exercises_per_session'].labels(
                        **label_dict
                    ).inc(profile.exercises_get_in_session)
                    logger.debug(
                        f'Session ended for user {profile.user_id}: '
                        f'{session_duration}'
                    )
                else:
                    session_duration = (
                        now - profile.session_started_at
                    ).total_seconds()
                    logger.debug(
                        f'Session duration for user {profile.user_id}: '
                        f'{session_duration}'
                    )
                    active_users_label_counts[label_tuple] += 1

            for label_tuple in all_possible_active_user_labels:
                label_dict = dict(
                    zip(
                        backend_user_metrics_label_names,
                        label_tuple,
                        strict=False,
                    )
                )
                count = active_users_label_counts.get(label_tuple, 0)
                BACKEND_USER_METRICS['active'].labels(**label_dict).set(count)
            logger.info('Users metrics updated.')
    except Exception as e:
        logger.error(f'Error in metrics update loop: {e}')


async def metrics_loop():
    while True:
        await update_user_sessions_metrics()
        await asyncio.sleep(UPDATE_USER_METRICS_INTERVAL)
