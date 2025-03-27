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
from app.core.value_objects.answer import Answer

logger = logging.getLogger(__name__)


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        llm_service: LLMProvider,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service

    async def get_or_create_new_exercise(
        self,
        user: User,
    ) -> Optional[Exercise]:
        # TODO: Добавить обработку исключений:
        #  What happens if the LLM service raises an exception?
        #   (можно запускать get_exercise_for_repetition, как вариант)
        #  What happens if a repository method raises an exception?

        await self._generate_new_exercise(user)

        language_level = LanguageLevel.get_new_exercise_level(
            user.language_level
        )

        # TODO: написать логику выбора типа задания, пока зглушка
        exercise_type = ExerciseType.FILL_IN_THE_BLANK
        # TODO: разобраться с топиками, пока зглушка
        topic = ExerciseTopic.GENERAL

        exercise = await self.exercise_repository.get_new_exercise(
            user=user,
            language_level=language_level,
            exercise_type=exercise_type,
            topic=topic,
        )
        if exercise is None:
            exercise = await self.get_exercise_for_repetition(user)

        return exercise

    async def _generate_new_exercise(
        self,
        user: User,
    ) -> None:
        async def _generate_and_save_new_exercise(
            user: User,
            exercise_type: ExerciseType,
            topic: ExerciseTopic,
        ) -> Exercise:
            try:
                exercise, answer = await self.llm_service.generate_exercise(
                    user, user.language_level, exercise_type, topic
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
            except GeneratorExit:
                logger.warning('LLM request was interrupted')
                raise

        exercises_count = await self.exercise_repository.count_new_exercises(
            user,
            user.language_level,
        )

        if exercises_count < MIN_EXERCISE_COUNT_TO_GENERATE_NEW:
            # TODO: написать логику выбора типа задания, пока зглушка
            exercise_type = ExerciseType.FILL_IN_THE_BLANK
            # TODO: разобраться с топиками, пока зглушка
            topic = ExerciseTopic.GENERAL

            asyncio.create_task(
                _generate_and_save_new_exercise(
                    user,
                    exercise_type,
                    topic,
                )
            )

    async def get_exercise_for_repetition(
        self,
        user: User,
    ) -> Optional[Exercise]:
        return await self.exercise_repository.get_exercise_for_repetition(
            user,
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_repository.get_by_id(exercise_id)

    async def validate_exercise_answer(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAnswer:
        if exercise.exercise_id is None:
            raise ValueError('Exercise ID must not be None')
        exercise_answer = (
            await self.exercise_answer_repository.get_by_exercise_and_answer(
                exercise.exercise_id, answer
            )
        )
        if not exercise_answer:
            repo = self.exercise_answer_repository
            correct_answers = [
                exercise_answer.answer
                for exercise_answer in (
                    await repo.get_correct_answers_by_exercise_id(
                        exercise_id=exercise.exercise_id
                    )
                )
            ]
            is_correct, feedback = await self.llm_service.validate_attempt(
                user, exercise, answer, correct_answers
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

    async def new_exercise_attempt(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
        is_correct: Optional[bool],
        feedback: Optional[str],
        exercise_answer_id: Optional[int] = None,
    ) -> ExerciseAttempt:
        if exercise.exercise_id is None:
            raise ValueError('Exercise ID must not be None')
        exercise_attempt = ExerciseAttempt(
            attempt_id=None,
            user_id=user.user_id,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=is_correct,
            feedback=feedback,
            exercise_answer_id=exercise_answer_id,
        )
        exercise_attempt = await self.exercise_attempt_repository.save(
            exercise_attempt
        )
        return exercise_attempt

    async def update_exercise_attempt(
        self,
        attempt_id: int,
        is_correct: bool,
        feedback: Optional[str],
        exercise_answer_id: int,
    ) -> ExerciseAttempt:
        updated_exercise_attempt = (
            await self.exercise_attempt_repository.update(
                attempt_id=attempt_id,
                is_correct=is_correct,
                feedback=feedback,
                exercise_answer_id=exercise_answer_id,
            )
        )
        return updated_exercise_attempt
