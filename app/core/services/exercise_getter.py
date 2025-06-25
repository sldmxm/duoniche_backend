import asyncio
import logging
from typing import Optional

from app.core.configs.enums import ExerciseType, LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.texts import get_text
from app.core.entities.exercise import Exercise
from app.core.interfaces.llm_provider import LLMProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.metrics import BACKEND_EXERCISE_METRICS

logger = logging.getLogger(__name__)


class ExerciseGetter:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        llm_service: LLMProvider,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service
        self.background_exercise_generation_task: Optional[asyncio.Task] = None

    async def get_next_exercise(
        self,
        user_id: int,
        target_language: str,
        user_language: str,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
        language_level: LanguageLevel,
    ) -> Optional[Exercise]:
        exercise = await self.exercise_repository.get_new_exercise(
            user_id=user_id,
            target_language=target_language,
            language_level=language_level,
            exercise_type=exercise_type,
            topic=topic,
        )

        if exercise:
            exercise.exercise_text = get_text(
                exercise.exercise_type, user_language
            )
            logger.info(
                f'New exercise from db ({exercise_type.value}, {topic.value}, '
                f'{language_level.value}): {exercise}'
            )
            return exercise

        for is_same_type in (True, False):
            any_new_exercise = (
                await self.exercise_repository.get_any_new_exercise(
                    user_id=user_id,
                    target_language=target_language,
                    exercise_type=exercise_type if is_same_type else None,
                )
            )
            if any_new_exercise:
                any_new_exercise.exercise_text = get_text(
                    any_new_exercise.exercise_type,
                    user_language,
                )
                logger.info(
                    f'New exercise from db, but not 100% as requested: '
                    f'{any_new_exercise}'
                )
                return any_new_exercise

        exercise_for_repetition = await self.get_exercise_for_repetition(
            user_id=user_id,
            target_language=target_language,
            user_language=user_language,
        )
        if exercise_for_repetition:
            logger.info(
                f'Exercise for repetition'
                f'({exercise_type.value}, {topic.value}, '
                f'{language_level.value}): {exercise_for_repetition}'
            )
            BACKEND_EXERCISE_METRICS['sent_repetition'].labels(
                exercise_type=exercise_for_repetition.exercise_type.value,
                level=exercise_for_repetition.language_level.value,
            ).inc()
            return exercise_for_repetition

        return None

    async def get_exercise_for_repetition(
        self,
        user_id: int,
        target_language: str,
        user_language: str,
    ) -> Optional[Exercise]:
        exercise_for_repetition_with_mistake = (
            await self.exercise_repository.get_mistake_repetition(
                user_id=user_id,
                target_language=target_language,
            )
        )
        if exercise_for_repetition_with_mistake:
            exercise_for_repetition_with_mistake.exercise_text = get_text(
                exercise_for_repetition_with_mistake.exercise_type,
                user_language,
            )
            return exercise_for_repetition_with_mistake

        any_for_repetition = (
            await self.exercise_repository.get_any_for_repetition(
                user_id=user_id,
                target_language=target_language,
            )
        )
        if any_for_repetition:
            any_for_repetition.exercise_text = get_text(
                any_for_repetition.exercise_type,
                user_language,
            )
            return exercise_for_repetition_with_mistake

        return None

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_repository.get_by_id(exercise_id)
