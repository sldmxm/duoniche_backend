import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx

from app.core.configs.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.generation.persona import Persona
from app.core.entities.exercise import Exercise
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
from app.utils.html_cleaner import clean_html_for_telegram
from app.utils.language_code_converter import (
    convert_iso639_language_code_to_full_name,
)

logger = logging.getLogger(__name__)

ASSESSOR_EXERCISE_TYPES_EXCLUDE = (ExerciseType.CHOOSE_ACCENT,)


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

    async def generate_detailed_report_text(
        self,
        context: dict,
        user_language: str,
        target_language: str,
    ) -> str:
        """
        Generates a detailed, LLM-powered weekly report with error analysis.
        """
        system_prompt_template = (
            'You are an experienced and supportive language learning coach '
            'for {target_language}. '
            'Your task is to generate a detailed weekly learning report '
            'for a user. The length of the report must be less than 3500 '
            'characters.'
            'The report must be written in {user_language} and addressed '
            'directly to the user (e.g., "You...", "Your..."). '
            'The tone should be encouraging, positive, and motivating, '
            'even when discussing areas for improvement. \n'
            'For text formating use *only* thees tags <b>, <i>, <u>, <code>, '
            "<s>. Don't use <ul>, <li>, <br>, <h>-like. \n"
            'Use emojis if it improves readability.\n\n'
            '**Report Structure (Strictly Follow):**\n\n'
            '1.  **Progress This Week:**\n'
            '    *   Summarize the number of exercises completed and overall '
            'accuracy (percentage).\n'
            '    *   Identify the 2-3 most frequently studied grammar and '
            'vocabulary topics based on the exercises done.\n\n'
            '2.  **Main Challenges:**\n'
            '    *   Based on incorrect attempts, pinpoint specific grammar '
            'and vocabulary topics where the user struggled most.\n'
            '    *   Focus on recurring error patterns. Avoid repeating '
            'topics from "Progress This Week" unless they were also a '
            'significant challenge.\n\n'
            '3.  **Error Examples & Explanations:**\n'
            '    *   Select 2-3 common or illustrative error types from the '
            'provided incorrect attempts.\n'
            '    *   For each, provide:\n'
            '        *   The original exercise task/question (if available, '
            'otherwise describe the context).\n'
            "        *   The user's incorrect answer.\n"
            '        *   The correct answer.\n'
            "        *   A concise explanation of why the user's answer was "
            'incorrect, focusing on the specific error.\n\n'
            '4.  **Comparison with Previous Report (If Applicable):**\n'
            '    *   If data for comparison is available (e.g., from a short '
            'summary of previous performance), comment on positive changes in '
            'accuracy, activity level, or improvement in specific topics.\n\n'
            '5.  **Recommendations for Next Week:**\n'
            '    *   Suggest 2-3 key areas for the user to focus on, such '
            'as topics to review or new areas to explore.\n'
            '    *   Prioritize topics where accuracy was low or those that '
            'were newly introduced and challenging.\n\n'
            '**Output Guidelines:**\n'
            '-   Generate a well-structured text with clear, concise, and '
            'non-repetitive phrasing.\n'
            '-   Maintain a supportive yet specific and actionable style '
            'throughout the report.'
        )

        user_prompt_template = (
            "Here is the context for the user's weekly report:\n"
            'Detailed Summary of Activity (topics studied, common errors '
            'based on tags) for previous week:\n'
            '{prev_summary}\n\n'
            'Detailed Summary of Activity (topics studied, common errors '
            'based on tags) for this week:\n'
            '{current_summary}\n\n'
            'Examples of Incorrect Attempts This Week (includes feedback '
            'given at the time of attempt, exercise tags, and error tags):\n'
            '{incorrect_attempts_str}\n\n'
            'Based on all this information, please write the detailed '
            "'Weekly Report' section by section, "
            'focusing on in-depth analysis and actionable advice as outlined '
            'in the system prompt. '
            'Pay special attention to analyzing the incorrect attempts to '
            'provide meaningful examples and explanations.'
        )

        user_language_for_prompt = convert_iso639_language_code_to_full_name(
            user_language
        )

        formatted_system_prompt = system_prompt_template.format(
            target_language=target_language,
            user_language=user_language_for_prompt,
        )

        incorrect_attempts_str_parts = []
        if context.get('incorrect_attempts'):
            for i, attempt_info in enumerate(
                context.get('incorrect_attempts', [])
            ):
                part = (
                    f"Attempt {i + 1}:\n"
                    f"  - User's incorrect answer was related to exercise "
                    f"covering tags: {attempt_info.get('exercise_tags')}\n"
                    f"  - The error was classified with tags: "
                    f"{attempt_info.get('error_tags')}\n"
                    f"  - Feedback given to user at the time: "
                    f"\"{attempt_info.get('feedback')}\""
                )
                incorrect_attempts_str_parts.append(part)
            incorrect_attempts_str = '\n'.join(incorrect_attempts_str_parts)
        else:
            incorrect_attempts_str = (
                'No specific incorrect attempts data provided for detailed '
                'analysis this week.'
            )

        full_prompt = (
            f"{formatted_system_prompt}\n\n"
            f"{user_prompt_template.format(
                prev_summary=context.get('prev_summary', 'N/A'),
                current_summary=context.get('current_summary', 'N/A'),
                incorrect_attempts_str=incorrect_attempts_str
                )}"
        )

        response = await self.model.ainvoke(full_prompt)

        report_text = clean_html_for_telegram(response.content)

        return report_text
