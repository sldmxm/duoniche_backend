import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.db import async_session_maker
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)

logger = logging.getLogger(__name__)

REPORT_GENERATION_INTERVAL_SECONDS = 60 * 60 * 24 * 7  # 7 days
MIN_ATTEMPTS_FOR_REPORT = 5
TOP_TAGS_COUNT = 7


def _format_tags_for_summary(
    tags_dict: dict,
    label: str,
    top_n: int = TOP_TAGS_COUNT,
) -> Optional[str]:
    """Helper function to format a list of tags and their counts."""
    if not tags_dict:
        return None

    sorted_tags = sorted(
        tags_dict.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:top_n]

    if not sorted_tags:
        return None

    tags_str = ', '.join(
        [f'{tag} ({count} times)' for tag, count in sorted_tags]
    )
    return f'{label}: {tags_str}.'


def _prepare_summary_context(summary: dict) -> str:
    """
    Formats the aggregated data into a text context for an LLM.
    """
    if not summary or summary.get('total_attempts', 0) == 0:
        return ''

    total = summary['total_attempts']
    correct = summary['correct_attempts']
    accuracy = (correct / total) * 100 if total > 0 else 0

    parts = [
        f'Over the last 7 days, you completed {total} exercises with '
        f'{accuracy:.0f}% accuracy.'
    ]

    exercise_grammar_summary = _format_tags_for_summary(
        summary.get('grammar_tags', {}), 'You focused on grammar topics'
    )
    if exercise_grammar_summary:
        parts.append(exercise_grammar_summary)

    exercise_vocab_summary = _format_tags_for_summary(
        summary.get('vocab_tags', {}), 'You focused on vocabulary topics'
    )
    if exercise_vocab_summary:
        parts.append(exercise_vocab_summary)

    error_grammar_summary = _format_tags_for_summary(
        summary.get('error_grammar_tags', {}),
        'Your most common grammar errors were related to',
    )
    if error_grammar_summary:
        parts.append(error_grammar_summary)

    error_vocab_summary = _format_tags_for_summary(
        summary.get('error_vocab_tags', {}),
        'Your most common vocabulary errors were related to',
    )
    if error_vocab_summary:
        parts.append(error_vocab_summary)

    return ' '.join(parts)


async def run_report_generation_cycle(
    # llm_service: LLMService, # Phase 6
):
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    # week_start_date = week_ago.date() # Phase 6

    async with async_session_maker() as session:
        user_profile_repo = SQLAlchemyUserBotProfileRepository(session)
        attempt_repo = SQLAlchemyExerciseAttemptRepository(session)
        # report_repo = SQLAlchemyUserReportRepository(session) # Phase 6

        active_profiles = (
            await user_profile_repo.get_active_profiles_for_reporting(
                since=week_ago,
            )
        )

        logger.info(
            f'Found {len(active_profiles)} active users for weekly report '
            'generation.',
        )

        for profile in active_profiles:
            summary = await attempt_repo.get_period_summary_for_user_and_bot(
                user_id=profile.user_id,
                bot_id=profile.bot_id.value,
                start_date=week_ago,
            )

            if (
                not summary
                or summary.get('total_attempts', 0) < MIN_ATTEMPTS_FOR_REPORT
            ):
                logger.info(
                    f'Skipping report for user {profile.user_id}/'
                    f'{profile.bot_id.value} due to low activity.',
                )
                continue

            summary_context = _prepare_summary_context(summary)
            if not summary_context:
                continue

            logger.info(
                f'Prepared summary for user {profile.user_id}/'
                f'{profile.bot_id.value}: {summary_context}',
            )

        await session.commit()


async def report_generator_worker_loop(
    stop_event: asyncio.Event,
):
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
