import asyncio
import logging
from datetime import datetime, timezone

from app.config import settings
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
) -> bool:
    try:
        async with exercise_generation_semaphore:
            language_level = LanguageLevel.get_next_exercise_level(
                settings.default_language_level
            )
            topic = ExerciseTopic.get_next_topic()

            if exercise_type == ExerciseType.CHOOSE_ACCENT:
                if target_language == BotID.BG.value:
                    generator = choose_accent_generator
                    exercise, answer = await generator.generate(
                        user_language=settings.default_user_language
                    )
                    created_by = 'scrapper'
                else:
                    logger.warning(
                        f'Skipping CHOOSE_ACCENT generation for non-BG '
                        f'language: {target_language}'
                    )
                    return False
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
                return True
            else:
                logger.warning(
                    f'Skipping save for exercise type '
                    f'{exercise_type.value} for {target_language} '
                    f'as it was not generated (exercise_data '
                    f'or answer_data is None).'
                )
                return False

    except ChooseAccentGenerationError as e:
        logger.warning(f'Failed to generate CHOOSE_ACCENT exercise: {e}')
        return False

    except Exception as e:
        logger.error(
            f'Error during exercise generation '
            f'and saving ({exercise_type}): {e}',
            exc_info=True,
        )
        return False


async def exercise_stock_refill(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
):
    try:
        tasks = []
        async with async_session_maker() as session:
            exercise_repo = SQLAlchemyExerciseRepository(session)
            available_counts_by_lang_type = (
                await exercise_repo.count_untouched_exercises()
            )

            all_target_languages = [bot_id.value for bot_id in BotID]
            all_exercise_types = list(ExerciseType)

            for lang in all_target_languages:
                if lang not in available_counts_by_lang_type:
                    available_counts_by_lang_type[lang] = {}

                for ex_type in all_exercise_types:
                    count = available_counts_by_lang_type.get(lang, {}).get(
                        ex_type.value, 0
                    )

                    logger.info(
                        f'Untouched exercises: Language: {lang}, '
                        f'Type: {ex_type.value}, Count: {count}'
                    )

                    BACKEND_EXERCISE_METRICS['untouched_exercises'].labels(
                        exercise_language=lang,
                    ).set(count)

                    if count < MIN_EXERCISE_COUNT_TO_GENERATE_NEW:
                        to_generate = (
                            MIN_EXERCISE_COUNT_TO_GENERATE_NEW - count
                        )
                        logger.info(
                            f'Need to generate {to_generate} exercises '
                            f'for {lang}, type {ex_type.value}'
                        )
                        for _ in range(to_generate):
                            tasks.append(
                                generate_and_save_exercise(
                                    user_language=settings.default_user_language,
                                    target_language=lang,
                                    exercise_type=ex_type,
                                    llm_service=llm_service,
                                    choose_accent_generator=choose_accent_generator,
                                )
                            )

            if tasks:
                logger.info(
                    f'Starting generation of {len(tasks)} '
                    f'new exercises in batch.'
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_generations = 0
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.warning(
                            f'Exercise generation task {i} in batch '
                            f'resulted in an error (see previous logs): '
                            f'{type(result).__name__}'
                        )
                    elif result is True:
                        successful_generations += 1
                logger.info(
                    f'Finished generation batch. Successful: '
                    f'{successful_generations}/{len(tasks)}'
                )

    except Exception as e:
        logger.error(
            f'Error in exercise_stock_refill ' f'main logic: {e}',
            exc_info=True,
        )


async def exercise_stock_refill_loop(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
    stop_event: asyncio.Event,
):
    logger.info('Exercise stock refill worker started.')
    try:
        while not stop_event.is_set():
            logger.info('Starting exercise refill cycle...')
            try:
                await exercise_stock_refill(
                    llm_service=llm_service,
                    choose_accent_generator=choose_accent_generator,
                )
            except Exception as e:
                logger.error(
                    f'Exercise refill cycle failed: {e}', exc_info=True
                )

            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(), timeout=EXERCISE_REFILL_INTERVAL
                )
                logger.info(
                    'Exercise stock refill: stop event '
                    'received during sleep interval.'
                )
                break
            except asyncio.TimeoutError:
                pass
            except asyncio.CancelledError:
                logger.info(
                    'Exercise stock refill: loop task cancelled '
                    'during sleep interval.'
                )
                raise
    except asyncio.CancelledError:
        logger.info('Exercise stock refill loop was cancelled.')
    finally:
        logger.info('Exercise stock refill loop terminated.')
