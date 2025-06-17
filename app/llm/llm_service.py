import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.core.entities.exercise import Exercise
from app.core.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.generation.config import ExerciseTopic
from app.core.generation.persona import Persona
from app.core.interfaces.llm_provider import LLMProvider
from app.core.value_objects.answer import Answer
from app.llm.assessors.quality_assessor import (
    ExerciseQualityAssessor,
    RejectedByAssessor,
)
from app.llm.factories import (
    ExerciseGeneratorFactory,
    ExerciseValidatorFactory,
)
from app.llm.llm_base import BaseLLMService
from app.metrics import BACKEND_LLM_METRICS
from app.utils.language_code_converter import (
    convert_iso639_language_code_to_full_name,
)

logger = logging.getLogger(__name__)

ASSESSOR_EXERCISE_TYPES_EXCLUDE = (ExerciseType.CHOOSE_ACCENT,)


class ReportLLMOutput(BaseModel):
    short_report: str = Field(
        description='A concise, summary version of the weekly report,'
        ' 2-3 sentences long and encouraging.'
    )

    full_report: str = Field(
        description='A detailed, comprehensive version of the weekly report '
        'with sections for progress, common mistakes, '
        'and suggestions.'
    )


class LLMService(BaseLLMService, LLMProvider):
    def __init__(self, http_client: httpx.AsyncClient, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.http_client = http_client
        self.exercise_quality_assessor = ExerciseQualityAssessor(
            *args, **kwargs
        )

    async def generate_exercise(
        self,
        user_language: str,
        target_language: str,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
        persona: Optional[Persona] = None,
    ) -> tuple[Exercise, Answer]:
        """Generate exercise for user based on exercise type."""
        generator = ExerciseGeneratorFactory.create_generator(
            exercise_type=exercise_type,
            llm_service=self,
            http_client=self.http_client,
        )

        with (
            BACKEND_LLM_METRICS['exercises_creation_time']
            .labels(
                exercise_type=exercise_type.value,
                level=language_level.value,
                user_language=user_language,
                target_language=target_language,
                llm_model=self.model.model_name,
            )
            .time()
        ):
            user_language_for_prompt = (
                convert_iso639_language_code_to_full_name(user_language)
            )

            (
                new_exercise,
                new_answer,
                exercise_for_quality_assessor,
            ) = await generator.generate(
                user_language=user_language_for_prompt,
                user_language_code=user_language,
                target_language=target_language,
                language_level=language_level,
                topic=topic,
                persona=persona,
            )

            if exercise_type not in ASSESSOR_EXERCISE_TYPES_EXCLUDE:
                try:
                    await self.exercise_quality_assessor.assess(
                        exercise=exercise_for_quality_assessor,
                        user_language=user_language_for_prompt,
                        target_language=target_language,
                    )
                except RejectedByAssessor as e:
                    logger.warning(f'Exercise rejected by assessor {e}')
                    new_exercise.status = ExerciseStatus.REJECTED_BY_ASSESSOR
                    timestamp = datetime.now(timezone.utc).strftime(
                        '%Y-%m-%d %H:%M:%S UTC'
                    )
                    issues_str = (
                        ', '.join(e.issues)
                        if e.issues
                        else 'No specific issues provided by LLM.'
                    )
                    comment_log_entry = (
                        f'Rejected by Quality Assessor at {timestamp}\n'
                        f'  Assessor Issues: {issues_str}'
                    )
                    if new_exercise.comments:
                        new_exercise.comments += f'\n---\n{comment_log_entry}'
                    else:
                        new_exercise.comments = comment_log_entry

        BACKEND_LLM_METRICS['exercises_created'].labels(
            exercise_type=exercise_type.value,
            level=language_level.value,
            user_language=user_language,
            target_language=target_language,
            llm_model=self.model.model_name,
        ).inc()

        return new_exercise, new_answer

    async def validate_attempt(
        self,
        user_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str, Dict[str, List[str]]]:
        """Validate user's answer to the exercise."""
        validator = ExerciseValidatorFactory.create_validator(
            exercise_type=exercise.exercise_type,
            llm_service=self,
        )

        target_language = exercise.exercise_language
        user_language_for_prompt = convert_iso639_language_code_to_full_name(
            user_language
        )

        with (
            BACKEND_LLM_METRICS['verification_time']
            .labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
                user_language=user_language,
                target_language=target_language,
                llm_model=self.model.model_name,
            )
            .time()
        ):
            is_correct, feedback, error_tags = await validator.validate(
                user_language=user_language_for_prompt,
                target_language=target_language,
                exercise=exercise,
                answer=answer,
            )

        BACKEND_LLM_METRICS['exercises_verified'].labels(
            exercise_type=exercise.exercise_type.value,
            level=exercise.language_level.value,
            user_language=user_language,
            target_language=target_language,
            llm_model=self.model.model_name,
        ).inc()

        return is_correct, feedback, error_tags

    async def generate_report_text(
        self, summary_context: str, user_language: str
    ) -> Optional[tuple[str, str]]:
        """Generates a weekly progress report using the LLM."""
        parser = PydanticOutputParser(pydantic_object=ReportLLMOutput)

        system_prompt = (
            'You are a supportive and insightful language learning coach. '
            'Your task is to write a weekly progress report '
            'for a user based on the provided summary of their activity. '
            'The report must be in {user_language}. '
            'The tone should be encouraging, positive, and motivating, '
            'even when pointing out areas for improvement. '
            'Start with a positive affirmation. Use markdown for formatting '
            'the full report (e.g., bold headings like **Progress Summary**).'
        )

        user_prompt = (
            "Here is the user's activity summary for the last 7 days:\n"
            '---\n'
            '{summary_context}\n'
            '---\n\n'
            'Please generate a short (2-3 sentences) and a full (detailed) '
            'progress report based on this data. '
            'For the full report, structure it with clear, friendly headings '
            "in {user_language} (e.g., 'Progress Summary', 'Areas to "
            "Focus On', 'Keep Going!'). "
            'Highlight both strengths and common errors. Provide a positive '
            'and actionable closing statement.'
            '\n\n{format_instructions}'
        )

        chat_prompt = ChatPromptTemplate.from_messages(
            [
                ('system', system_prompt),
                ('user', user_prompt),
            ]
        )

        chain = await self.create_llm_chain(
            chat_prompt, parser, is_chat_prompt=True
        )

        user_language_full_name = convert_iso639_language_code_to_full_name(
            user_language
        )

        request_data = {
            'summary_context': summary_context,
            'user_language': user_language_full_name,
            'format_instructions': parser.get_format_instructions(),
        }

        try:
            report_output: ReportLLMOutput = await self.run_llm_chain(
                chain, request_data
            )
            return report_output.short_report, report_output.full_report
        except Exception as e:
            logger.error(
                f'Failed to generate report for user language {user_language} '
                f'with summary: "{summary_context[:100]}...". Error: {e}',
                exc_info=True,
            )

            return None
