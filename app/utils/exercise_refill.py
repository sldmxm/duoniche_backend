import asyncio
import logging
from datetime import datetime, timezone

from app.core.consts import DEFAULT_LANGUAGE_LEVEL, DEFAULT_USER_LANGUAGE
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.db.db import async_session_maker
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.llm.llm_service import LLMService

logger = logging.getLogger(__name__)

MIN_EXERCISE_COUNT_TO_GENERATE_NEW = 10
EXERCISE_REFILL_INTERVAL = 60
ERROR_PAUSE_INTERVAL = 10

exercise_generation_semaphore = asyncio.Semaphore(5)


async def generate_and_save_exercise(
    user_language: str,
    target_language: str,
) -> None:
    async with exercise_generation_semaphore:
        llm_service = LLMService()

        language_level = LanguageLevel.get_next_exercise_level(
            DEFAULT_LANGUAGE_LEVEL
        )
        exercise_type = ExerciseType.get_next_type()
        topic = ExerciseTopic.get_next_topic()

        try:
            exercise, answer = await llm_service.generate_exercise(
                user_language=user_language,
                target_language=target_language,
                language_level=language_level,
                exercise_type=exercise_type,
                topic=topic,
            )
            async with async_session_maker() as session:
                exercise_repository = SQLAlchemyExerciseRepository(session)
                exercise_answer_repository = (
                    SQLAlchemyExerciseAnswerRepository(session)
                )
                exercise = await exercise_repository.save(exercise)

                if exercise.exercise_id:
                    right_answer = ExerciseAnswer(
                        answer_id=None,
                        exercise_id=exercise.exercise_id,
                        answer=answer,
                        is_correct=True,
                        created_by='LLM',
                        feedback='',
                        feedback_language='',
                        created_at=datetime.now(timezone.utc),
                    )
                    await exercise_answer_repository.save(right_answer)

                await session.commit()

        except Exception as e:
            logger.error(f'Error during exercise generation: {e}')


async def exercise_refill():
    try:
        async with async_session_maker() as session:
            exercise_repo = SQLAlchemyExerciseRepository(session)
            available_count = (
                await exercise_repo.count_untouched_exercises_by_language()
            )
            for exercise_language, count in available_count.items():
                if count < MIN_EXERCISE_COUNT_TO_GENERATE_NEW:
                    to_generate = MIN_EXERCISE_COUNT_TO_GENERATE_NEW - count
                    for _ in range(to_generate):
                        asyncio.create_task(
                            generate_and_save_exercise(
                                user_language=DEFAULT_USER_LANGUAGE,
                                target_language=exercise_language,
                            )
                        )

    except Exception as e:
        logger.error(f'Error in exercise refill loop: {e}')
        await asyncio.sleep(ERROR_PAUSE_INTERVAL)


async def exercise_refill_loop():
    while True:
        logger.info('Starting exercise refill loop...')
        await exercise_refill()
        await asyncio.sleep(EXERCISE_REFILL_INTERVAL)
