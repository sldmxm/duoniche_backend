import logging
from datetime import datetime, timedelta
from typing import Optional

from arq.connections import ArqRedis

from app.core.entities.user_bot_profile import UserBotProfile
from app.core.entities.user_report import UserReport
from app.core.enums import ReportStatus
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user_report import UserReportRepository
from app.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

INCORRECT_ATTEMPTS_FOR_LLM_NUMBER = 15
TOP_TAGS_COUNT = 7


class ReportNotFoundError(Exception):
    pass


class UserReportService:
    def __init__(
        self,
        user_report_repository: UserReportRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        arq_pool: ArqRedis,
        llm_service: LLMService,
    ):
        self.user_report_repo = user_report_repository
        self.attempt_repo = exercise_attempt_repository
        self.arq_pool = arq_pool
        self.llm_service = llm_service

    async def get_by_id(self, report_id: int) -> Optional[UserReport]:
        return await self.user_report_repo.get_by_id(report_id)

    async def get_by_id_and_user(
        self, report_id: int, user_id: int
    ) -> Optional[UserReport]:
        return await self.user_report_repo.get_by_id_and_user(
            report_id, user_id
        )

    async def request_detailed_report(
        self,
        profile: UserBotProfile,
    ) -> ReportStatus:
        """Handles a user's request for a detailed weekly report.

        It checks the status of the latest report. If a detailed report is
        already being generated or is ready, it returns a message.
        Otherwise, it enqueues a background task to generate the report.
        """
        if not profile:
            raise ReportNotFoundError()

        latest_report = await self.user_report_repo.get_latest_by_user_and_bot(
            user_id=profile.user_id, bot_id=profile.bot_id.value
        )

        if not latest_report:
            raise ReportNotFoundError(
                f'No weekly report found for user {profile.user_id}, '
                f'bot {profile.bot_id.value}'
            )

        if latest_report.status in [
            ReportStatus.GENERATING,
            ReportStatus.GENERATED,
            ReportStatus.SENT,
        ]:
            return latest_report.status

        await self.arq_pool.enqueue_job(
            'generate_and_send_detailed_report_arq',
            latest_report.report_id,
        )
        logger.info(
            f'Enqueued detailed report generation for report_id: '
            f'{latest_report.report_id}'
        )

        return ReportStatus.GENERATING

    async def generate_full_report_text(
        self,
        profile: UserBotProfile,
    ) -> str:
        """Generates the full report text content using an LLM."""

        latest_report = await self.user_report_repo.get_latest_by_user_and_bot(
            user_id=profile.user_id,
            bot_id=profile.bot_id.value,
        )

        if not latest_report:
            raise ReportNotFoundError(
                f'No report found for user {profile.user_id} and bot'
                f' {profile.bot_id.value}',
            )

        logger.info(
            f'Generating detailed report for user {profile.user_id} '
            f'(report_id: {latest_report.report_id}) on-demand.',
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
                user_id=profile.user_id,
                bot_id=profile.bot_id.value,
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
        current_summary = UserReportService._prepare_summary_context(
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
        prev_summary = UserReportService._prepare_summary_context(
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

        return full_report_text

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

        exercise_grammar_summary = UserReportService._format_tags_for_summary(
            summary.get('grammar_tags', {}),
            'You focused on grammar topics',
        )
        if exercise_grammar_summary:
            parts.append(exercise_grammar_summary)

        exercise_vocab_summary = UserReportService._format_tags_for_summary(
            summary.get('vocab_tags', {}),
            'You focused on vocabulary topics',
        )
        if exercise_vocab_summary:
            parts.append(exercise_vocab_summary)

        error_grammar_summary = UserReportService._format_tags_for_summary(
            summary.get('error_grammar_tags', {}),
            'Your most common grammar errors were related to',
        )
        if error_grammar_summary:
            parts.append(error_grammar_summary)

        error_vocab_summary = UserReportService._format_tags_for_summary(
            summary.get('error_vocab_tags', {}),
            'Your most common vocabulary errors were related to',
        )
        if error_vocab_summary:
            parts.append(error_vocab_summary)

        return ' '.join(parts)
