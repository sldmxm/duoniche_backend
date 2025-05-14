import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.enums import ExerciseType
from app.core.interfaces.llm_provider import LLMProvider
from app.core.interfaces.translate_provider import TranslateProvider
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.async_task_cache import (
    AsyncTaskCache,
    deserialize_exercise_answer,
    deserialize_exercise_attempt,
    serialize_exercise_answer,
    serialize_exercise_attempt,
)
from app.core.value_objects.answer import Answer
from app.metrics import BACKEND_EXERCISE_METRICS

logger = logging.getLogger(__name__)


class AttemptValidator:
    def __init__(
        self,
        exercise_attempt_repository: ExerciseAttemptRepository,
        exercise_answers_repository: ExerciseAnswerRepository,
        llm_service: LLMProvider,
        translator: TranslateProvider,
        async_task_cache: AsyncTaskCache,
    ):
        self.exercise_attempt_repository = exercise_attempt_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service
        self.translator = translator
        self.async_task_cache = async_task_cache

    async def validate_exercise_attempt(
        self,
        user_id: int,
        user_language: str,
        last_exercise_at: Optional[datetime],
        exercise: Exercise,
        answer: Answer,
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
                    if a.feedback_language == user_language
                ),
                None,
            )
            other_lang_answer: Optional[ExerciseAnswer] = next(
                (
                    a
                    for a in all_answers
                    if a.feedback_language != user_language
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

        async def _handle_exercise_attempt(
            user_id: int,
            user_language: str,
            exercise: Exercise,
            answer: Answer,
        ) -> ExerciseAttempt:
            db_answer = await _get_answer_from_db()
            if db_answer and (
                db_answer.is_correct
                or db_answer.feedback_language == user_language
            ):
                if exercise.exercise_id is None:
                    raise ValueError(
                        'Cannot validate an exercise without an ID'
                    )

                exercise_attempt = ExerciseAttempt(
                    attempt_id=None,
                    user_id=user_id,
                    exercise_id=exercise.exercise_id,
                    answer=answer,
                    is_correct=db_answer.is_correct,
                    feedback=db_answer.feedback,
                    answer_id=db_answer.answer_id,
                )
                return await self.exercise_attempt_repository.create(
                    exercise_attempt
                )

            if exercise.exercise_id is None:
                raise ValueError('Cannot validate an exercise without an ID')

            pre_attempt = ExerciseAttempt(
                attempt_id=None,
                user_id=user_id,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=None,
                feedback=None,
                answer_id=None,
            )

            pre_saved_attempt = await self.exercise_attempt_repository.create(
                pre_attempt
            )
            logger.debug(f'Pre saved user attempt {pre_saved_attempt}')

            if exercise.exercise_type == ExerciseType.CHOOSE_ACCENT:
                repo = self.exercise_answer_repository
                correct_answers = (
                    await repo.get_correct_answers_by_exercise_id(
                        exercise.exercise_id
                    )
                )
                feedback = ', '.join(
                    [a.answer.get_answer_text() for a in correct_answers]
                )
                incorrect_answer = ExerciseAnswer(
                    answer_id=None,
                    exercise_id=exercise.exercise_id,
                    answer=answer,
                    is_correct=False,
                    feedback=feedback,
                    feedback_language=user_language,
                    created_at=datetime.now(timezone.utc),
                    created_by=f'auto:{user_id}',
                )
                new_answer = await self.exercise_answer_repository.create(
                    incorrect_answer
                )
            else:
                if db_answer and db_answer.feedback_language != user_language:
                    new_answer = await self.copy_answer_translate_feedback(
                        exercise=exercise,
                        answer=db_answer,
                        user_language=user_language,
                    )
                else:
                    new_answer = await self.llm_validate_and_save_new_answer(
                        user_id=user_id,
                        user_language=user_language,
                        exercise=exercise,
                        answer=answer,
                    )

            if pre_saved_attempt.attempt_id is None:
                raise ValueError(
                    'Exercise attempt attempt_id must not be None'
                )
            if new_answer.answer_id is None:
                raise ValueError('Exercise answer answer_id must not be None')

            updated_exercise_attempt = (
                await self.exercise_attempt_repository.update(
                    attempt_id=pre_saved_attempt.attempt_id,
                    is_correct=new_answer.is_correct,
                    feedback=new_answer.feedback,
                    answer_id=new_answer.answer_id,
                )
            )
            logger.debug(
                f'Exercise attempt updated: {updated_exercise_attempt}'
            )
            return updated_exercise_attempt

        BACKEND_EXERCISE_METRICS['attempts'].labels(
            exercise_type=exercise.exercise_type.value,
            level=exercise.language_level.value,
        ).inc()
        if last_exercise_at:
            answer_duration = (
                datetime.now(timezone.utc) - last_exercise_at
            ).total_seconds()
            BACKEND_EXERCISE_METRICS['attempt_time'].labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
            ).observe(answer_duration)
        with (
            BACKEND_EXERCISE_METRICS['validation_time']
            .labels(
                exercise_type=exercise.exercise_type.value,
                level=exercise.language_level.value,
            )
            .time()
        ):
            attempt_key = (
                f'backend_validate_attempt'
                f'_{user_id}'
                f'_{exercise.exercise_id}'
                f'_{hash(answer.get_answer_text())}'
            )

            exercise_attempt = await self.async_task_cache.get_or_create_task(
                key=attempt_key,
                task_func=lambda: _handle_exercise_attempt(
                    user_id=user_id,
                    user_language=user_language,
                    exercise=exercise,
                    answer=answer,
                ),
                serializer=serialize_exercise_attempt,
                deserializer=deserialize_exercise_attempt,
            )
            if exercise_attempt.is_correct:
                BACKEND_EXERCISE_METRICS['incorrect_attempts'].labels(
                    exercise_type=exercise.exercise_type.value,
                    level=exercise.language_level.value,
                ).inc()

        return exercise_attempt

    async def llm_validate_and_save_new_answer(
        self,
        user_id: int,
        user_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> ExerciseAnswer:
        async def _inner(
            user_id: int,
            user_language: str,
            exercise: Exercise,
            answer: Answer,
        ) -> ExerciseAnswer:
            if exercise.exercise_id is None:
                raise ValueError('Cannot validate an exercise without an ID')
            is_correct, feedback = await self.llm_service.validate_attempt(
                user_language=user_language,
                exercise=exercise,
                answer=answer,
            )
            exercise_answer = ExerciseAnswer(
                answer_id=None,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=is_correct,
                feedback=feedback,
                feedback_language=user_language,
                created_at=datetime.now(timezone.utc),
                created_by=f'LLM:user:{user_id}',
            )
            saved_answer = await self.exercise_answer_repository.create(
                exercise_answer
            )
            return saved_answer

        cache_key = (
            'backend_validation'
            f'_{exercise.exercise_id}'
            f'_{hash(answer.get_answer_text())}'
        )
        validated = await self.async_task_cache.get_or_create_task(
            key=cache_key,
            task_func=lambda: _inner(
                user_id=user_id,
                user_language=user_language,
                exercise=exercise,
                answer=answer,
            ),
            serializer=serialize_exercise_answer,
            deserializer=deserialize_exercise_answer,
        )
        if validated.answer_id is None:
            raise ValueError('Exercise answer answer_id must not be None')

        logger.debug(f'Validation answer retrieved/generated: {validated}')
        return validated

    async def copy_answer_translate_feedback(
        self,
        exercise: Exercise,
        answer: ExerciseAnswer,
        user_language: str,
    ) -> ExerciseAnswer:
        async def _inner(
            exercise: Exercise,
            answer: ExerciseAnswer,
            target_language: str,
        ) -> ExerciseAnswer:
            new_answer = answer.model_copy(deep=True)
            new_answer.answer_id = None
            new_answer.feedback = await self.translator.translate_feedback(
                feedback=answer.feedback,
                user_language=user_language,
                exercise_data=exercise.data.model_dump_json(),
                user_answer=answer.answer.get_answer_text(),
                exercise_language=exercise.exercise_language,
            )
            new_answer.feedback_language = target_language
            new_answer.created_at = datetime.now(timezone.utc)
            new_answer.created_by = f'translated_answer:{answer.answer_id}'

            saved_answer = await self.exercise_answer_repository.create(
                new_answer
            )
            return saved_answer

        logger.info(
            f'Begin translation process for {answer} ' f'to {user_language}'
        )
        cache_key = f'backend_translation_{answer.answer_id}_{user_language}'
        translated = await self.async_task_cache.get_or_create_task(
            key=cache_key,
            task_func=lambda: _inner(
                exercise,
                answer,
                user_language,
            ),
            serializer=serialize_exercise_answer,
            deserializer=deserialize_exercise_answer,
        )
        if translated.answer_id is None:
            raise ValueError('Exercise answer answer_id must not be None')
        logger.info(f'Translated answer retrieved/generated: {translated}')
        return translated
