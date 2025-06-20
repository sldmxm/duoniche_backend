import logging
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx

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
    ) -> Tuple[bool, str]:
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
            is_correct, feedback = await validator.validate(
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

        return is_correct, feedback
