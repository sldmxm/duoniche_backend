import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.consts import MIN_EXERCISE_COUNT_TO_GENERATE_NEW
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.interfaces.llm_provider import LLMProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.cache import ValidationCache
from app.core.services.cache import (
    validation_cache as default_validation_cache,
)
from app.core.value_objects.answer import Answer

logger = logging.getLogger(__name__)


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        llm_service: LLMProvider,
        validation_cache: ValidationCache = default_validation_cache,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service
        self.validation_cache = validation_cache
        self.background_exercise_generation_task: Optional[asyncio.Task] = None

    async def get_or_create_next_exercise(
        self,
        user: User,
    ) -> Optional[Exercise]:
        async def generate_new_exercise_if_needed(
            user: User,
            exercise_type: ExerciseType,
            topic: ExerciseTopic,
            language_level: LanguageLevel,
        ) -> None:
            exercises_count = (
                await self.exercise_repository.count_new_exercises(
                    user,
                    language_level,
                )
            )
            if exercises_count < MIN_EXERCISE_COUNT_TO_GENERATE_NEW:
                self.background_exercise_generation_task = asyncio.create_task(
                    self.generate_and_save_new_exercise(
                        user=user,
                        exercise_type=exercise_type,
                        topic=topic,
                        language_level=language_level,
                    )
                )

        async def get_some_exercise() -> Exercise:
            if language_level != user.language_level:
                user_level_exercise = (
                    await self.exercise_repository.get_new_exercise(
                        user=user,
                        language_level=user.language_level,
                        exercise_type=exercise_type,
                        topic=topic,
                    )
                )
                if user_level_exercise:
                    return user_level_exercise

            exercise_for_repetition = await self.get_exercise_for_repetition(
                user
            )
            if exercise_for_repetition:
                return exercise_for_repetition

            if self.background_exercise_generation_task:
                return await self.background_exercise_generation_task

            return await self.generate_and_save_new_exercise(
                user=user,
                exercise_type=exercise_type,
                topic=topic,
                language_level=language_level,
            )

        # TODO: Добавить обработку исключений:
        #  What happens if the LLM service raises an exception?
        #   (можно запускать get_exercise_for_repetition, как вариант)
        #  What happens if a repository method raises an exception?

        language_level = LanguageLevel.get_next_exercise_level(
            user.language_level
        )
        # TODO: написать логику выбора типа задания, пока заглушка
        exercise_type = ExerciseType.FILL_IN_THE_BLANK
        # TODO: разобраться с топиками, пока заглушка
        topic = ExerciseTopic.GENERAL
        await generate_new_exercise_if_needed(
            user=user,
            exercise_type=exercise_type,
            topic=topic,
            language_level=language_level,
        )

        exercise = await self.exercise_repository.get_new_exercise(
            user=user,
            language_level=language_level,
            exercise_type=exercise_type,
            topic=topic,
        )
        if exercise is None:
            exercise = await get_some_exercise()

        return exercise

    async def generate_and_save_new_exercise(
        self,
        user: User,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> Exercise:
        exercise, answer = await self.llm_service.generate_exercise(
            user, language_level, exercise_type, topic
        )
        exercise = await self.exercise_repository.save(exercise)
        if exercise.exercise_id:
            right_answer = ExerciseAnswer(
                answer_id=None,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=True,
                created_by='LLM',
                feedback='',
                created_at=datetime.now(),
            )
            await self.exercise_answer_repository.save(right_answer)
        return exercise

    async def get_exercise_for_repetition(
        self,
        user: User,
    ) -> Optional[Exercise]:
        return await self.exercise_repository.get_exercise_for_repetition(
            user,
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_repository.get_by_id(exercise_id)

    async def validate_exercise_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAttempt:
        """
        Validate a user's answer to an exercise,
        handling caching and database operations.
        """
        if exercise.exercise_id is None:
            raise ValueError('Exercise ID must not be None')

        exercise_attempt = ExerciseAttempt(
            attempt_id=None,
            user_id=user.user_id,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=None,
            feedback=None,
            exercise_answer_id=None,
        )

        exercise_answer = (
            await self.exercise_answer_repository.get_by_exercise_and_answer(
                exercise.exercise_id, answer
            )
        )
        if exercise_answer:
            exercise_attempt.is_correct = exercise_answer.is_correct
            exercise_attempt.feedback = exercise_answer.feedback
            exercise_attempt.exercise_answer_id = exercise_answer.answer_id

            exercise_attempt = await self.exercise_attempt_repository.save(
                exercise_attempt
            )

        else:
            exercise_attempt = await self.exercise_attempt_repository.save(
                exercise_attempt
            )
            cache_key = (
                'validation'
                f'_{exercise.exercise_id}'
                f'_{hash(answer.get_answer_text())}'
            )
            validation_result = (
                await self.validation_cache.get_or_create_validation(
                    key=cache_key,
                    validation_func=lambda: self.llm_validate_exercise_answer(
                        user,
                        exercise,
                        answer,
                    ),
                )
            )
            if exercise_attempt.attempt_id is None:
                raise ValueError(
                    'Exercise attempt attempt_id must not be None'
                )
            if validation_result.answer_id is None:
                raise ValueError('Exercise answer answer_id must not be None')

            exercise_attempt = await self.exercise_attempt_repository.update(
                attempt_id=exercise_attempt.attempt_id,
                is_correct=validation_result.is_correct,
                feedback=validation_result.feedback,
                exercise_answer_id=validation_result.answer_id,
            )

        return exercise_attempt

    async def llm_validate_exercise_answer(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAnswer:
        if exercise.exercise_id is None:
            raise ValueError('Exercise ID must not be None')

        is_correct, feedback = await self.llm_service.validate_attempt(
            user, exercise, answer
        )
        exercise_answer = ExerciseAnswer(
            answer_id=None,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=is_correct,
            feedback=feedback,
            created_at=datetime.now(),
            # TODO: Вынести в константу
            #  ИЛИ добавить атрибуты в модель, чтобы понимать,
            #  как принято решение о правильности ответа
            created_by=f'LLM:user:{user.user_id}',
        )

        exercise_answer = await self.exercise_answer_repository.save(
            exercise_answer
        )
        return exercise_answer
