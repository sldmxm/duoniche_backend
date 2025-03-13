from datetime import datetime
from typing import Optional

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.interfaces.llm_provider import LLMProvider
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.value_objects.answer import Answer


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        cached_answer_repository: CachedAnswerRepository,
        llm_service: LLMProvider,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.cached_answer_repository = cached_answer_repository
        self.llm_service = llm_service

    async def get_or_create_new_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Optional[Exercise]:
        # TODO: Добавить обработку исключений:
        #  What happens if the LLM service raises an exception?
        #   (можно запускать get_exercise_for_repetition, как вариант)
        #  What happens if a repository method raises an exception?

        # TODO: Добавить проверку количества доступных пользователю заданий,
        #  если их меньше N (константа в конфиге),
        #  то генерировать новые заранее

        exercise = await self.exercise_repository.get_new_exercise(
            user, language_level, exercise_type
        )
        if not exercise:
            exercise = await self.llm_service.generate_exercise(
                user, language_level, exercise_type
            )
            exercise = await self.exercise_repository.save(exercise)
        return exercise

    async def get_exercise_for_repetition(
        self, user: User, language_level: str, exercise_type: str
    ) -> Optional[Exercise]:
        return await self.exercise_repository.get_exercise_for_repetition(
            user, language_level, exercise_type
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_repository.get_by_id(exercise_id)

    async def validate_exercise_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAttempt:
        if exercise.exercise_id is None:
            raise ValueError('Exercise ID must not be None')
        cached_answer = (
            await self.cached_answer_repository.get_by_exercise_and_answer(
                exercise.exercise_id, answer
            )
        )
        if cached_answer:
            exercise_attempt = ExerciseAttempt(
                attempt_id=None,
                user_id=user.user_id,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=cached_answer.is_correct,
                feedback=cached_answer.feedback,
                cached_answer_id=cached_answer.answer_id,
            )
        else:
            is_correct, feedback = await self.llm_service.validate_attempt(
                user, exercise, answer
            )
            cached_answer = CachedAnswer(
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

            cached_answer = await self.cached_answer_repository.save(
                cached_answer
            )
            exercise_attempt = ExerciseAttempt(
                attempt_id=None,
                user_id=user.user_id,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=is_correct,
                feedback=feedback,
                cached_answer_id=cached_answer.answer_id,
            )
        exercise_attempt = await self.exercise_attempt_repository.save(
            exercise_attempt
        )
        return exercise_attempt

    async def _check_cached_answer(
        self, exercise_id: int, answer: Answer
    ) -> CachedAnswer | None:
        return await self.cached_answer_repository.get_by_exercise_and_answer(
            exercise_id, answer
        )
