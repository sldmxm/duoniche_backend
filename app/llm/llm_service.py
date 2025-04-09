from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.interfaces.llm_provider import LLMProvider
from app.core.value_objects.answer import Answer
from app.llm.factories import (
    ExerciseGeneratorFactory,
    ExerciseValidatorFactory,
)
from app.llm.llm_base import BaseLLMService
from app.metrics import BACKEND_LLM_METRICS


class LLMService(BaseLLMService, LLMProvider):
    async def generate_exercise(
        self,
        user: User,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> tuple[Exercise, Answer]:
        """Generate exercise for user based on exercise type."""
        generator = ExerciseGeneratorFactory.create_generator(
            exercise_type, self
        )

        with (
            BACKEND_LLM_METRICS['exercises_creation_time']
            .labels(
                exercise_type=exercise_type.value,
                level=language_level.value,
                user_language=user.user_language,
                target_language=user.target_language,
                llm_model=self.model.model_name,
            )
            .time()
        ):
            new_exercise, new_answer = await generator.generate(
                user=user, language_level=language_level, topic=topic
            )

        BACKEND_LLM_METRICS['exercises_created'].labels(
            exercise_type=exercise_type.value,
            level=language_level.value,
            user_language=user.user_language,
            target_language=user.target_language,
            llm_model=self.model.model_name,
        ).inc()

        return new_exercise, new_answer

    async def validate_attempt(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        """Validate user's answer to the exercise."""
        validator = ExerciseValidatorFactory.create_validator(
            exercise.exercise_type, self
        )

        with (
            BACKEND_LLM_METRICS['verification_time']
            .labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
                user_language=user.user_language,
                target_language=user.target_language,
                llm_model=self.model.model_name,
            )
            .time()
        ):
            is_correct, feedback = await validator.validate(
                user, exercise, answer
            )

        BACKEND_LLM_METRICS['exercises_verified'].labels(
            exercise_type=exercise.exercise_type.value,
            level=exercise.language_level.value,
            user_language=user.user_language,
            target_language=user.target_language,
            llm_model=self.model.model_name,
        ).inc()

        return is_correct, feedback
