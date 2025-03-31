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
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service
        self.translator = translator
        self.async_task_cache = async_task_cache
        self.background_exercise_generation_task: Optional[asyncio.Task] = None

    async def get_or_create_next_exercise(
        self,
        user: User,
    ) -> Optional[Exercise]:
        async def generate_new_exercise_if_needed() -> None:
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
        logger.debug(f'Next exercise level: {language_level} for user {user}')
        # TODO: написать логику выбора типа задания, пока заглушка
        exercise_type = ExerciseType.FILL_IN_THE_BLANK
        # TODO: разобраться с топиками, пока заглушка
        topic = ExerciseTopic.GENERAL
        await generate_new_exercise_if_needed()

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
                feedback_language='',
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

        async def _get_answer_from_db() -> Optional[ExerciseAnswer]:
            if exercise.exercise_id is None:
                raise ValueError('Cannot validate an exercise without an ID')
            all_answers = (
                await self.exercise_answer_repository.get_all_by_user_answer(
                    exercise.exercise_id, answer
                )
            )
            logger.debug(f'All answers from DB: {all_answers}')
            correct_answer: Optional[ExerciseAnswer] = next(
                (a for a in all_answers if a.is_correct), None
            )
            user_lang_answer: Optional[ExerciseAnswer] = next(
                (
                    a
                    for a in all_answers
                    if a.feedback_language == user.user_language
                ),
                None,
            )
            other_lang_answer: Optional[ExerciseAnswer] = next(
                (
                    a
                    for a in all_answers
                    if a.feedback_language != user.user_language
                ),
                None,
            )
            if correct_answer:
                chosen_answer = correct_answer
            elif user_lang_answer:
                chosen_answer = user_lang_answer
            elif other_lang_answer:
                chosen_answer = other_lang_answer
            else:
                chosen_answer = None
            return chosen_answer

        def serialize_exercise_answer(obj: ExerciseAnswer) -> bytes:
            return obj.model_dump_json().encode('utf-8')

        def deserialize_exercise_answer(data: bytes) -> ExerciseAnswer:
            return ExerciseAnswer.model_validate_json(data)

        if exercise.exercise_id is None:
            raise ValueError('Cannot validate an exercise without an ID')

        exercise_attempt = ExerciseAttempt(
            attempt_id=None,
            user_id=user.user_id,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=None,
            feedback=None,
            exercise_answer_id=None,
        )

        db_answer = await _get_answer_from_db()

        if db_answer and (
            db_answer.is_correct
            or db_answer.feedback_language == user.user_language
        ):
            exercise_attempt.is_correct = db_answer.is_correct
            exercise_attempt.feedback = db_answer.feedback
            exercise_attempt.exercise_answer_id = db_answer.answer_id
            return await self.exercise_attempt_repository.save(
                exercise_attempt
            )

        pre_saved_attempt = await self.exercise_attempt_repository.save(
            exercise_attempt
        )

        if db_answer and db_answer.feedback_language != user.user_language:
            logger.debug(
                f'Begin translation process for {db_answer} '
                f'to {user.user_language}'
            )
            cache_key = (
                f'translation_{db_answer.answer_id}_{user.user_language}'
            )
            translated = await self.async_task_cache.get_or_create_task(
                key=cache_key,
                task_func=lambda: self.copy_answer_with_translated_feedback(
                    db_answer,
                    user.user_language,
                ),
                serializer=serialize_exercise_answer,
                deserializer=deserialize_exercise_answer,
            )
            if translated.answer_id is None:
                raise ValueError('Exercise answer answer_id must not be None')
            new_answer = translated
            logger.debug(
                f'Translated answer retrieved/generated: {new_answer}'
            )

        else:
            cache_key = (
                'validation'
                f'_{exercise.exercise_id}'
                f'_{hash(answer.get_answer_text())}'
            )

            validated = await self.async_task_cache.get_or_create_task(
                key=cache_key,
                task_func=lambda: self.llm_validate_and_save_exercise_answer(
                    user,
                    exercise,
                    answer,
                ),
                serializer=serialize_exercise_answer,
                deserializer=deserialize_exercise_answer,
            )
            if validated.answer_id is None:
                raise ValueError('Exercise answer answer_id must not be None')

            logger.debug(f'Validation answer retrieved/generated: {validated}')
            new_answer = validated

        if pre_saved_attempt.attempt_id is None:
            raise ValueError('Exercise attempt attempt_id must not be None')

        exercise_attempt = await self.exercise_attempt_repository.update(
            attempt_id=pre_saved_attempt.attempt_id,
            is_correct=new_answer.is_correct,
            feedback=new_answer.feedback,
            exercise_answer_id=new_answer.answer_id,
        )

        return exercise_attempt

    async def llm_validate_and_save_exercise_answer(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAnswer:
        if exercise.exercise_id is None:
            raise ValueError('Cannot validate an exercise without an ID')
        is_correct, feedback = await self.llm_service.validate_attempt(
            user, exercise, answer
        )
        exercise_answer = ExerciseAnswer(
            answer_id=None,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=is_correct,
            feedback=feedback,
            feedback_language=user.user_language,
            created_at=datetime.now(),
            created_by=f'LLM:user:{user.user_id}',
        )
        saved_answer = await self.exercise_answer_repository.save(
            exercise_answer
        )
        return saved_answer

    async def copy_answer_with_translated_feedback(
        self,
        answer: ExerciseAnswer,
        target_language: str,
    ) -> ExerciseAnswer:
        new_answer = answer.model_copy(deep=True)
        new_answer.answer_id = None
        new_answer.feedback = await self.translator.translate_text(
            text=answer.feedback, target_language=target_language
        )
        new_answer.feedback_language = target_language
        new_answer.created_by = f'translated_answer:{answer.answer_id}'

        saved_answer = await self.exercise_answer_repository.save(new_answer)
        return saved_answer
