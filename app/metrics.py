import asyncio
import collections
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Set

from prometheus_client import Counter, Gauge, Histogram

from app.db.db import async_session_maker
from app.db.models import DBUserBotProfile
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)

logger = logging.getLogger(__name__)

UPDATE_USER_METRICS_INTERVAL = 60
SESSION_TTL_SINCE_LAST_EXERCISE = timedelta(minutes=5)

METRIC_PREFIX = 'backend_'

backend_exercise_metrics_label_names = [
    'exercise_type',
    'level',
]
BACKEND_EXERCISE_METRICS = {
    'sent': Counter(
        METRIC_PREFIX + 'exercise_sent_total',
        'Total number of exercises sent to users',
        labelnames=backend_exercise_metrics_label_names,
    ),
    'sent_repetition': Counter(
        METRIC_PREFIX + 'exercise_sent_repetition_total',
        'Total number of repetition exercises sent to users',
        labelnames=backend_exercise_metrics_label_names,
    ),
    'attempts': Counter(
        METRIC_PREFIX + 'exercise_attempt_total',
        'Total number of user attempts to solve exercises',
        labelnames=backend_exercise_metrics_label_names,
    ),
    'attempt_time': Histogram(
        METRIC_PREFIX + 'exercise_time_for_attempt_seconds',
        'Time spent by user for answer an exercise',
        labelnames=backend_exercise_metrics_label_names,
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    ),
    'validation_time': Histogram(
        METRIC_PREFIX + 'exercise_validation_time_seconds',
        "Time spent validating a user's solution",
        labelnames=backend_exercise_metrics_label_names,
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    ),
    'incorrect_attempts': Counter(
        METRIC_PREFIX + 'exercise_error_total',
        'Total number of incorrect attempts made by users in exercises',
        labelnames=backend_exercise_metrics_label_names,
    ),
    'untouched_exercises': Gauge(
        METRIC_PREFIX + 'untouched_exercises_total',
        'Total number of untouched exercises',
        labelnames=['exercise_language'],
    ),
}

backend_user_metrics_label_names = [
    'cohort',
    'plan',
    'target_language',
    'user_language',
    'language_level',
]
BACKEND_USER_METRICS = {
    'new': Counter(
        METRIC_PREFIX + 'new_users_total',
        'Total number of new users',
        labelnames=backend_user_metrics_label_names,
    ),
    'active': Gauge(
        METRIC_PREFIX + 'active_users_total',
        'Total number of active users',
        labelnames=backend_user_metrics_label_names,
    ),
    'session_length': Histogram(
        METRIC_PREFIX + 'user_session_length_seconds',
        'Length of user sessions in seconds',
        labelnames=backend_user_metrics_label_names,
        buckets=(10, 30, 60, 120, 300, 600, 900, 1800, 3600),
    ),
    'exercises_per_session': Counter(
        METRIC_PREFIX + 'exercises_per_session',
        'Number of exercises per session',
        labelnames=backend_user_metrics_label_names,
    ),
    'full_sessions': Counter(
        METRIC_PREFIX + 'full_sessions_total',
        'Total number of session ended freeze.',
        labelnames=backend_user_metrics_label_names,
    ),
    'frozen_attempts': Counter(
        METRIC_PREFIX + 'frozen_attempts_total',
        'Total number of attempts to start exercises when frozen',
        labelnames=backend_user_metrics_label_names,
    ),
}

backend_llm_metrics_label_names = [
    'exercise_type',
    'level',
    'user_language',
    'target_language',
    'llm_model',
]
BACKEND_LLM_METRICS = {
    'exercises_created': Counter(
        METRIC_PREFIX + 'exercise_created_total',
        'Total number of exercises created by LLM',
        labelnames=backend_llm_metrics_label_names,
    ),
    'exercises_rejected': Counter(
        METRIC_PREFIX + 'exercise_rejected_total',
        'Total number of exercises created and then rejected by LLM',
        labelnames=backend_llm_metrics_label_names,
    ),
    'exercises_creation_time': Histogram(
        METRIC_PREFIX + 'exercise_creation_time_seconds',
        'Time spent for creation an exercise by LLM',
        labelnames=backend_llm_metrics_label_names,
        buckets=(3, 5, 7, 9, 10, 11, 12, 13, 14, 15),
    ),
    'verification_time': Histogram(
        METRIC_PREFIX + 'exercise_verification_time_seconds',
        "Time spent for verification a user's solution by LLM",
        labelnames=backend_llm_metrics_label_names,
        buckets=(3, 5, 7, 9, 10, 11, 12, 13, 14, 15),
    ),
    'exercises_verified': Counter(
        METRIC_PREFIX + 'exercise_verified_total',
        'Total number of exercise verifications by LLM',
        labelnames=backend_llm_metrics_label_names,
    ),
    'input_tokens': Counter(
        METRIC_PREFIX + 'llm_input_tokens_total',
        'Total number of input tokens used by LLM',
        labelnames=backend_llm_metrics_label_names,
    ),
    'output_tokens': Counter(
        METRIC_PREFIX + 'llm_output_tokens_total',
        'Total number of output tokens used by LLM',
        labelnames=backend_llm_metrics_label_names,
    ),
}

backend_translator_metrics_label_names = [
    'target_language',
]
BACKEND_TRANSLATOR_METRICS = {
    'translations': Counter(
        METRIC_PREFIX + 'translations_total',
        'Total number of translations',
        labelnames=backend_translator_metrics_label_names,
    ),
    'translations_chars': Counter(
        METRIC_PREFIX + 'translations_chars_total',
        'Total number of translations',
        labelnames=backend_translator_metrics_label_names,
    ),
    'translation_time': Histogram(
        METRIC_PREFIX + 'translation_time_seconds',
        'Time for translation',
        labelnames=backend_translator_metrics_label_names,
        buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
    ),
}

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
