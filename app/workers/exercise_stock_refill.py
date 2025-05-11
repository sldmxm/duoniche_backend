import asyncio
import logging
from datetime import datetime, timezone

from app.core.consts import (
    DEFAULT_LANGUAGE_LEVEL,
    DEFAULT_TARGET_LANGUAGE,
    DEFAULT_USER_LANGUAGE,
)
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user_bot_profile import BotID
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.db.db import async_session_maker
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.db.repositories.exercise_answers import (
    SQLAlchemyExerciseAnswerRepository,
)
from app.llm.llm_service import LLMService
from app.metrics import BACKEND_EXERCISE_METRICS
from app.services.choose_accent_generator import (
    ChooseAccentGenerationError,
    ChooseAccentGenerator,
)

logger = logging.getLogger(__name__)

MIN_EXERCISE_COUNT_TO_GENERATE_NEW = 5
EXERCISE_REFILL_INTERVAL = 60

exercise_generation_semaphore = asyncio.Semaphore(5)


async def generate_and_save_exercise(
    user_language: str,
    target_language: str,
    exercise_type: ExerciseType,
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
) -> None:
    try:
        async with exercise_generation_semaphore:
            language_level = LanguageLevel.get_next_exercise_level(
                DEFAULT_LANGUAGE_LEVEL
            )
            topic = ExerciseTopic.get_next_topic()
            if exercise_type == ExerciseType.CHOOSE_ACCENT:
                if target_language == BotID.BG.value:
                    try:
                        (
                            exercise,
                            answer,
                        ) = await choose_accent_generator.generate(
                            user_language=DEFAULT_USER_LANGUAGE
                        )
                    except ChooseAccentGenerationError as e:
                        logger.warning(
                            f'Failed to generate CHOOSE_ACCENT exercise: {e}'
                        )
                        return
                    created_by = 'scrapper'
            else:
                exercise, answer = await llm_service.generate_exercise(
                    user_language=user_language,
                    target_language=target_language,
                    language_level=language_level,
                    exercise_type=exercise_type,
                    topic=topic,
                )
                created_by = 'LLM'
            if exercise and answer:
                async with async_session_maker() as session:
                    exercise_repository = SQLAlchemyExerciseRepository(session)
                    exercise_answer_repository = (
                        SQLAlchemyExerciseAnswerRepository(session)
                    )
                    exercise = await exercise_repository.create(exercise)

                    if exercise.exercise_id:
                        right_answer = ExerciseAnswer(
                            answer_id=None,
                            exercise_id=exercise.exercise_id,
                            answer=answer,
                            is_correct=True,
                            created_by=created_by,
                            feedback='',
                            feedback_language='',
                            created_at=datetime.now(timezone.utc),
                        )
                        await exercise_answer_repository.create(right_answer)
                    await session.commit()
            else:
                logger.info(
                    f'Skipping save for exercise type {exercise_type} '
                    f'as it was not generated.'
                )

    except Exception as e:
        logger.error(
            f'Error during exercise generation '
            f'and saving ({exercise_type}): {e}',
            exc_info=True,
        )


async def exercise_stock_refill(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
):
    try:
        tasks = []
        async with async_session_maker() as session:
            exercise_repo = SQLAlchemyExerciseRepository(session)
            available_count = await exercise_repo.count_untouched_exercises()
            if not available_count:
                available_count = {DEFAULT_TARGET_LANGUAGE: {}}
            all_exercise_types = list(ExerciseType)
            for exercise_language in available_count:
                for exercise_type in all_exercise_types:
                    count = available_count.get(exercise_language, {}).get(
                        exercise_type.value, 0
                    )

                    logger.info(
                        f'Untouched exercises: Language: {exercise_language}, '
                        f'Type: {exercise_type.value} Count: {count}'
                    )
                    BACKEND_EXERCISE_METRICS['untouched_exercises'].labels(
                        exercise_language=exercise_language
                    ).set(count)

                    if count < MIN_EXERCISE_COUNT_TO_GENERATE_NEW:
                        to_generate = (
                            MIN_EXERCISE_COUNT_TO_GENERATE_NEW - count
                        )
                        for _ in range(to_generate):
                            tasks.append(
                                generate_and_save_exercise(
                                    user_language=DEFAULT_USER_LANGUAGE,
                                    target_language=exercise_language,
                                    exercise_type=exercise_type,
                                    llm_service=llm_service,
                                    choose_accent_generator=choose_accent_generator,
                                )
                            )

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(
                            f'Exercise generation task {i} in batch '
                            f'resulted in an error '
                            f'(already logged): {type(result).__name__}'
                        )

    except Exception as e:
        logger.error(
            f'Error in exercise_stock_refill ' f'main logic: {e}',
            exc_info=True,
        )


async def exercise_stock_refill_loop(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
):
    while True:
        logger.info('Starting exercise refill loop...')
        await exercise_stock_refill(
            llm_service=llm_service,
            choose_accent_generator=choose_accent_generator,
        )
        await asyncio.sleep(EXERCISE_REFILL_INTERVAL)
