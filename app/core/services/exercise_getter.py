import asyncio
import logging
from datetime import datetime
from typing import Optional

from app.core.consts import (
    MIN_EXERCISE_COUNT_TO_GENERATE_NEW,
)
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.interfaces.llm_provider import LLMProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.texts import get_text

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

    async def get_or_create_next_exercise(
        self,
        user: User,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
        language_level: LanguageLevel,
    ) -> Optional[Exercise]:
        async def generate_new_exercise_if_needed() -> None:
            exercises_count = (
                await self.exercise_repository.count_new_exercises(
                    user,
                    language_level,
                )
            )
            logger.debug(
                f'New exercises count for user {user.user_id}: '
                f'{exercises_count}'
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

        async def get_any_exercise() -> Exercise:
            if language_level != user.language_level:
                user_level_general_exercise = (
                    await self.exercise_repository.get_new_exercise(
                        user=user,
                        language_level=user.language_level,
                        exercise_type=exercise_type,
                        topic=ExerciseTopic.GENERAL,
                    )
                )
                if user_level_general_exercise:
                    user_level_general_exercise.exercise_text = get_text(
                        user_level_general_exercise.exercise_type,
                        user.user_language,
                    )
                    logger.debug(
                        f'New exercise from db but standard level and topic'
                        f'({exercise_type.value}, {topic.value}, '
                        f'{language_level.value}): '
                        f'{user_level_general_exercise}'
                    )
                    return user_level_general_exercise

            exercise_for_repetition = await self.get_exercise_for_repetition(
                user
            )
            if exercise_for_repetition:
                exercise_for_repetition.exercise_text = get_text(
                    exercise_for_repetition.exercise_type, user.user_language
                )
                logger.debug(
                    f'Exercise for repetition from db only'
                    f'({exercise_type.value}, {topic.value}, '
                    f'{language_level.value}): {exercise_for_repetition}'
                )
                return exercise_for_repetition

            if self.background_exercise_generation_task:
                generated_task = await self.background_exercise_generation_task
                logger.debug(
                    f'New generated exercise from background task'
                    f'({exercise_type.value}, {topic.value}, '
                    f'{language_level.value}): {generated_task}'
                )
                generated_task.exercise_text = get_text(
                    generated_task.exercise_type, user.user_language
                )
                return generated_task

            generated_task = await self.generate_and_save_new_exercise(
                user=user,
                exercise_type=exercise_type,
                topic=topic,
                language_level=language_level,
            )
            generated_task.exercise_text = get_text(
                generated_task.exercise_type, user.user_language
            )
            logger.debug(
                f'Slow New generated exercise'
                f'({exercise_type.value}, {topic.value}, '
                f'{language_level.value}): {generated_task}'
            )
            return generated_task

        await generate_new_exercise_if_needed()

        exercise = await self.exercise_repository.get_new_exercise(
            user=user,
            language_level=language_level,
            exercise_type=exercise_type,
            topic=topic,
        )

        if exercise:
            exercise.exercise_text = get_text(
                exercise.exercise_type, user.user_language
            )
            logger.debug(
                f'New exercise from db ({exercise_type.value}, {topic.value}, '
                f'{language_level.value}): {exercise}'
            )

        if exercise is None:
            exercise = await get_any_exercise()

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
                feedback_language='',
                created_at=datetime.now(),
            )
            await self.exercise_answer_repository.save(right_answer)
        return exercise

    async def get_exercise_for_repetition(
        self,
        user: User,
    ) -> Optional[Exercise]:
        exercise_for_repetition_with_mistake = (
            await self.exercise_repository.get_mistake_repetition(
                user,
            )
        )
        if exercise_for_repetition_with_mistake:
            return exercise_for_repetition_with_mistake

        return await self.exercise_repository.get_any_for_repetition(
            user,
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Optional[Exercise]:
        return await self.exercise_repository.get_by_id(exercise_id)
