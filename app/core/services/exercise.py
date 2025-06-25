import logging
from datetime import datetime
from typing import Optional

from app.config import settings
from app.core.configs.enums import ExerciseType, LanguageLevel
from app.core.configs.generation.config import ExerciseTopic
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.interfaces.llm_provider import LLMProvider
from app.core.interfaces.translate_provider import TranslateProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.async_task_cache import (
    AsyncTaskCache,
)
from app.core.services.attempt_validator import AttemptValidator
from app.core.services.exercise_getter import ExerciseGetter
from app.core.value_objects.answer import Answer

logger = logging.getLogger(__name__)


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        llm_service: LLMProvider,
        translator: TranslateProvider,
        async_task_cache: AsyncTaskCache,
    ):
        self.exercise_getter = ExerciseGetter(
            exercise_repository=exercise_repository,
            exercise_answers_repository=exercise_answers_repository,
            llm_service=llm_service,
        )
        self.attempt_validator = AttemptValidator(
            exercise_attempt_repository=exercise_attempt_repository,
            exercise_answers_repository=exercise_answers_repository,
            llm_service=llm_service,
            translator=translator,
            async_task_cache=async_task_cache,
        )

    async def get_next_exercise(
        self,
        user_id: int,
        target_language: str,
        user_language: str,
        exercise_type: ExerciseType = ExerciseType.FILL_IN_THE_BLANK,
        topic: ExerciseTopic = ExerciseTopic.GENERAL,
        language_level: LanguageLevel = settings.default_language_level,
    ) -> Optional[Exercise]:
        return await self.exercise_getter.get_next_exercise(
            user_id=user_id,
            target_language=target_language,
            user_language=user_language,
            exercise_type=exercise_type,
            topic=topic,
            language_level=language_level,
        )

    async def get_exercise_for_repetition(
        self,
        user_id: int,
        target_language: str,
        user_language: str,
    ) -> Optional[Exercise]:
        return await self.exercise_getter.get_exercise_for_repetition(
            user_id=user_id,
            target_language=target_language,
            user_language=user_language,
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_getter.get_exercise_by_id(exercise_id)

    async def validate_exercise_attempt(
        self,
        user_id: int,
        user_language: str,
        last_exercise_at: Optional[datetime],
        exercise: Exercise,
        answer: Answer,
    ) -> ExerciseAttempt:
        return await self.attempt_validator.validate_exercise_attempt(
            user_id=user_id,
            user_language=user_language,
            last_exercise_at=last_exercise_at,
            exercise=exercise,
            answer=answer,
        )
