import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
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
from app.core.services.async_task_cache import (
    async_task_cache as default_async_task_cache,
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
        async_task_cache: AsyncTaskCache = default_async_task_cache,
    ):
        self.exercise_attempt_repository = exercise_attempt_repository
        self.exercise_answer_repository = exercise_answers_repository
        self.llm_service = llm_service
        self.translator = translator
        self.async_task_cache = async_task_cache

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

        async def _handle_exercise_attempt(
            user: User,
            exercise: Exercise,
            answer: Answer,
        ) -> ExerciseAttempt:
            db_answer = await _get_answer_from_db()
            if db_answer and (
                db_answer.is_correct
                or db_answer.feedback_language == user.user_language
            ):
                if exercise.exercise_id is None:
                    raise ValueError(
                        'Cannot validate an exercise without an ID'
                    )

                exercise_attempt = ExerciseAttempt(
                    attempt_id=None,
                    user_id=user.user_id,
                    exercise_id=exercise.exercise_id,
                    answer=answer,
                    is_correct=db_answer.is_correct,
                    feedback=db_answer.feedback,
                    answer_id=db_answer.answer_id,
                )
                return await self.exercise_attempt_repository.save(
                    exercise_attempt
                )

            if exercise.exercise_id is None:
                raise ValueError('Cannot validate an exercise without an ID')

            pre_attempt = ExerciseAttempt(
                attempt_id=None,
                user_id=user.user_id,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=None,
                feedback=None,
                answer_id=None,
            )

            pre_saved_attempt = await self.exercise_attempt_repository.save(
                pre_attempt
            )
            logger.debug(f'Pre saved user attempt {pre_saved_attempt}')

            if db_answer and db_answer.feedback_language != user.user_language:
                new_answer = await self.copy_answer_translate_feedback(
                    db_answer, user.user_language
                )
            else:
                new_answer = await self.llm_validate_and_save_new_answer(
                    user, exercise, answer
                )

                if new_answer.feedback_language != user.user_language:
                    new_answer = await self.copy_answer_translate_feedback(
                        new_answer, user.user_language
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
        if user.last_exercise_at:
            answer_duration = (
                datetime.now(timezone.utc) - user.last_exercise_at
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
                f'validate_attempt'
                f'_{user.user_id}'
                f'_{exercise.exercise_id}'
                f'_{hash(answer.get_answer_text())}'
            )

            exercise_attempt = await self.async_task_cache.get_or_create_task(
                key=attempt_key,
                task_func=lambda: _handle_exercise_attempt(
                    user,
                    exercise,
                    answer,
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
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAnswer:
        async def _inner(
            user: User, exercise: Exercise, answer: Answer
        ) -> ExerciseAnswer:
            if exercise.exercise_id is None:
                raise ValueError('Cannot validate an exercise without an ID')
            is_correct, feedback = await self.llm_service.validate_attempt(
                user.user_language,
                user.target_language,
                exercise,
                answer,
            )
            exercise_answer = ExerciseAnswer(
                answer_id=None,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=is_correct,
                feedback=feedback,
                feedback_language=user.user_language,
                created_at=datetime.now(timezone.utc),
                created_by=f'LLM:user:{user.user_id}',
            )
            saved_answer = await self.exercise_answer_repository.save(
                exercise_answer
            )
            return saved_answer

        cache_key = (
            'validation'
            f'_{exercise.exercise_id}'
            f'_{hash(answer.get_answer_text())}'
        )
        validated = await self.async_task_cache.get_or_create_task(
            key=cache_key,
            task_func=lambda: _inner(
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
        return validated

    async def copy_answer_translate_feedback(
        self,
        db_answer: ExerciseAnswer,
        target_language: str,
    ) -> ExerciseAnswer:
        async def _inner(
            answer: ExerciseAnswer,
            target_language: str,
        ) -> ExerciseAnswer:
            new_answer = answer.model_copy(deep=True)
            new_answer.answer_id = None
            new_answer.feedback = await self.translator.translate_text(
                text=answer.feedback, target_language=target_language
            )
            new_answer.feedback_language = target_language
            new_answer.created_at = datetime.now(timezone.utc)
            new_answer.created_by = f'translated_answer:{answer.answer_id}'

            saved_answer = await self.exercise_answer_repository.save(
                new_answer
            )
            return saved_answer

        logger.info(
            f'Begin translation process for {db_answer} '
            f'to {target_language}'
        )
        cache_key = f'translation_{db_answer.answer_id}_{target_language}'
        translated = await self.async_task_cache.get_or_create_task(
            key=cache_key,
            task_func=lambda: _inner(
                db_answer,
                target_language,
            ),
            serializer=serialize_exercise_answer,
            deserializer=deserialize_exercise_answer,
        )
        if translated.answer_id is None:
            raise ValueError('Exercise answer answer_id must not be None')
        logger.info(f'Translated answer retrieved/generated: {translated}')
        return translated
