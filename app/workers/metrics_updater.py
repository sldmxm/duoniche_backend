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
                if not profile.user:
                    logger.warning(
                        f'Profile {profile.user_id}/{profile.bot_id} '
                        f'is missing user data. Skipping.'
                    )
                    continue
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

                session_ended = profile.session_frozen_until is not None or (
                    profile.last_exercise_at
                    and (
                        now - profile.last_exercise_at
                        > SESSION_TTL_SINCE_LAST_EXERCISE
                    )
                )

                if (
                    session_ended
                    and profile.session_started_at
                    and profile.last_exercise_at
                ):
                    session_duration = (
                        profile.last_exercise_at - profile.session_started_at
                    ).total_seconds()
                    if session_duration >= 0:
                        BACKEND_USER_METRICS['session_length'].labels(
                            **label_dict
                        ).observe(session_duration)
                        BACKEND_USER_METRICS['exercises_per_session'].labels(
                            **label_dict
                        ).inc(profile.exercises_get_in_session)
                        logger.debug(
                            f'Session ended for user {profile.user_id}'
                            f'/{profile.bot_id.value}: '
                            f'duration {session_duration}s, exercises '
                            f'{profile.exercises_get_in_session}'
                        )
                elif (
                    profile.session_started_at
                    and profile.last_exercise_at
                    and not session_ended
                ):
                    active_users_label_counts[label_tuple] += 1

            for existing_label_tuple in list(all_possible_active_user_labels):
                if existing_label_tuple not in active_users_label_counts:
                    label_dict_to_reset = dict(
                        zip(
                            backend_user_metrics_label_names,
                            existing_label_tuple,
                            strict=False,
                        )
                    )
                    BACKEND_USER_METRICS['active'].labels(
                        **label_dict_to_reset
                    ).set(0)

            for label_tuple, count in active_users_label_counts.items():
                label_dict_to_set = dict(
                    zip(
                        backend_user_metrics_label_names,
                        label_tuple,
                        strict=False,
                    )
                )
                BACKEND_USER_METRICS['active'].labels(**label_dict_to_set).set(
                    count
                )

            logger.info(
                f'Users metrics updated. Active sessions processed: '
                f'{sum(active_users_label_counts.values())}'
            )
    except Exception as e:
        logger.error(
            f'Error in update_user_sessions_metrics: {e}', exc_info=True
        )


async def metrics_loop(stop_event: asyncio.Event):
    logger.info('Metrics updater started.')
    try:
        while not stop_event.is_set():
            try:
                await update_user_sessions_metrics()
            except Exception as e:
                logger.error(
                    f'Metrics update cycle failed: {e}', exc_info=True
                )

            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=UPDATE_USER_METRICS_INTERVAL
                )
                logger.info(
                    'Metrics updater: stop event received '
                    'during sleep interval.'
                )
                break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                logger.info(
                    'Metrics updater: loop task cancelled '
                    'during sleep interval.'
                )
                raise
    except asyncio.CancelledError:
        logger.info('Metrics updater loop was cancelled.')
    finally:
        logger.info('Metrics updater loop terminated.')
