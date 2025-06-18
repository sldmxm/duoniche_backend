import logging
from datetime import datetime, timedelta
from typing import Optional

from app.core.entities.user_bot_profile import BotID
from app.core.entities.user_report import UserReport
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user_report import UserReportRepository
from app.core.services.user_bot_profile import UserBotProfileService
from app.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

INCORRECT_ATTEMPTS_FOR_LLM_NUMBER = 15
TOP_TAGS_COUNT = 7


class ReportNotFoundError(Exception):
    pass


class DetailedReportService:
    def __init__(
        self,
        user_report_repository: UserReportRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        user_bot_profile_service: UserBotProfileService,
        llm_service: LLMService,
    ):
        self.user_report_repo = user_report_repository
        self.attempt_repo = exercise_attempt_repository
        self.answer_repo = exercise_answers_repository
        self.user_bot_profile_service = user_bot_profile_service
        self.llm_service = llm_service

    async def generate_detailed_report(
        self,
        user_id: int,
        bot_id: BotID,
    ) -> UserReport:
        """
        Generates and returns the detailed weekly report for a user.

        - Fetches the latest report record.
        - If a full report already exists, returns it.
        - If not, it gathers necessary data, generates the full report
          via an LLM, updates the record, and returns it.

        Raises:
            ReportNotFoundError: If no weekly report record exists for
                                 the user.
        """
        profile = await self.user_bot_profile_service.get(
            user_id=user_id,
            bot_id=bot_id,
        )

        if not profile:
            raise ReportNotFoundError()

        latest_report = await self.user_report_repo.get_latest_by_user_and_bot(
            user_id=user_id,
            bot_id=bot_id.value,
        )

        if not latest_report:
            raise ReportNotFoundError(
                f'No report found for user {user_id} and bot {bot_id.value}',
            )

        if latest_report.full_report:
            logger.info(
                f'Full report for user {user_id} (report_id: '
                f'{latest_report.report_id}) already exists. Returning it.',
            )
            return latest_report

        logger.info(
            f'Generating detailed report for user {user_id} (report_id: '
            f'{latest_report.report_id}) on-demand.',
        )

        start_date_current = datetime.combine(
            latest_report.week_start_date,
            datetime.min.time(),
        )
        end_date_current = start_date_current + timedelta(days=7)
        end_date_prev = start_date_current
        start_date_prev = end_date_prev - timedelta(days=7)

        incorrect_attempts = (
            await self.attempt_repo.get_incorrect_attempts_with_details(
                user_id=user_id,
                bot_id=bot_id.value,
                start_date=start_date_current,
                end_date=end_date_current,
                limit=INCORRECT_ATTEMPTS_FOR_LLM_NUMBER,
            )
        )

        current_summary_data = (
            await self.attempt_repo.get_period_summary_for_user_and_bot(
                user_id=profile.user_id,
                bot_id=profile.bot_id.value,
                start_date=start_date_current,
                end_date=end_date_current,
            )
        )
        current_summary = DetailedReportService._prepare_summary_context(
            current_summary_data
        )

        prev_summary_data = (
            await self.attempt_repo.get_period_summary_for_user_and_bot(
                user_id=profile.user_id,
                bot_id=profile.bot_id.value,
                start_date=start_date_prev,
                end_date=end_date_prev,
            )
        )
        prev_summary = DetailedReportService._prepare_summary_context(
            prev_summary_data
        )

        context = {
            'prev_summary': prev_summary,
            'current_summary': current_summary,
            'incorrect_attempts': [
                item.model_dump() for item in incorrect_attempts
            ],
        }

        logger.info(f'Context for report:{context}')

        full_report_text = await (
            self.llm_service.generate_detailed_report_text(
                context=context,
                user_language=profile.user_language,
                target_language=profile.bot_id.value,
            )
        )

        latest_report.full_report = full_report_text
        updated_report = await self.user_report_repo.update(latest_report)

        logger.info(
            f'Successfully generated and saved full report '
            f'for user {user_id}.',
        )
        return updated_report

    @staticmethod
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
            [f'{tag} ({count} times)' for tag, count in sorted_tags],
        )
        return f'{label}: {tags_str}.'

    @staticmethod
    def _prepare_summary_context(summary) -> str:
        """
        Formats the aggregated data into a text context for an LLM.
        """

        if not summary or summary.get('total_attempts', 0) == 0:
            return ''

        active_days = summary.get('active_days', 0)
        total = summary['total_attempts']
        correct = summary['correct_attempts']
        accuracy = (correct / total) * 100 if total > 0 else 0

        parts = [
            f'Over the last 7 days, you you have been active for '
            f'{active_days} days and completed {total} exercises with '
            f'an accuracy of {accuracy:.0f}%.'
        ]

        exercise_grammar_summary = (
            DetailedReportService._format_tags_for_summary(
                summary.get('grammar_tags', {}),
                'You focused on grammar topics',
            )
        )
        if exercise_grammar_summary:
            parts.append(exercise_grammar_summary)

        exercise_vocab_summary = (
            DetailedReportService._format_tags_for_summary(
                summary.get('vocab_tags', {}),
                'You focused on vocabulary topics',
            )
        )
        if exercise_vocab_summary:
            parts.append(exercise_vocab_summary)

        error_grammar_summary = DetailedReportService._format_tags_for_summary(
            summary.get('error_grammar_tags', {}),
            'Your most common grammar errors were related to',
        )
        if error_grammar_summary:
            parts.append(error_grammar_summary)

        error_vocab_summary = DetailedReportService._format_tags_for_summary(
            summary.get('error_vocab_tags', {}),
            'Your most common vocabulary errors were related to',
        )
        if error_vocab_summary:
            parts.append(error_vocab_summary)

        return ' '.join(parts)
