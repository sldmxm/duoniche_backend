import logging
from typing import Optional

from app.core.consts import (
    DEFAULT_LANGUAGE_LEVEL,
)
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.interfaces.llm_provider import LLMProvider
from app.core.interfaces.translate_provider import TranslateProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.async_task_cache import (
    AsyncTaskCache,
)
from app.core.services.async_task_cache import (
    async_task_cache as default_async_task_cache,
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
        async_task_cache: AsyncTaskCache = default_async_task_cache,
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
        user: User,
        exercise_type: ExerciseType = ExerciseType.FILL_IN_THE_BLANK,
        topic: ExerciseTopic = ExerciseTopic.GENERAL,
        language_level: LanguageLevel = DEFAULT_LANGUAGE_LEVEL,
    ) -> Optional[Exercise]:
        return await self.exercise_getter.get_next_exercise(
            user, exercise_type, topic, language_level
        )

    async def get_exercise_for_repetition(
        self,
        user: User,
    ) -> Optional[Exercise]:
        return await self.exercise_getter.get_exercise_for_repetition(user)

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_getter.get_exercise_by_id(exercise_id)

    async def validate_exercise_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAttempt:
        return await self.attempt_validator.validate_exercise_attempt(
            user, exercise, answer
        )
