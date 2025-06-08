import asyncio
import logging
import random
from datetime import datetime, timezone
from typing import Optional, Tuple

import httpx

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user_bot_profile import BotID
from app.core.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.generation.config import ExerciseTopic
from app.core.generation.persona import Persona
from app.core.generation.selector import select_persona_for_topic
from app.core.value_objects.exercise import StoryComprehensionExerciseData
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
from app.services.file_storage_service import R2FileStorageService
from app.services.tts_service import GoogleTTSService

logger = logging.getLogger(__name__)

MIN_EXERCISE_COUNT_TO_GENERATE_NEW = 5
EXERCISE_REFILL_INTERVAL = 60 * 10
CHANCE_TO_GENERATE_PERSONA_FOR_TOPIC = 1
TTS_COOLDOWN_SECONDS = 60 * 60

EXCLUDE_TOPICS = [
    ExerciseTopic.TECH,
    ExerciseTopic.PHARMACY,
    ExerciseTopic.EMERGENCIES,
    ExerciseTopic.EDUCATION,
]

exercise_generation_semaphore = asyncio.Semaphore(5)

_tts_last_failure_timestamp: Optional[datetime] = None
_tts_cooldown_lock = asyncio.Lock()


async def is_tts_cooldown_active() -> bool:
    async with _tts_cooldown_lock:
        if _tts_last_failure_timestamp:
            return (
                datetime.now(timezone.utc) - _tts_last_failure_timestamp
            ).total_seconds() < TTS_COOLDOWN_SECONDS
        return False


async def set_tts_failure_timestamp():
    async with _tts_cooldown_lock:
        global _tts_last_failure_timestamp
        _tts_last_failure_timestamp = datetime.now(timezone.utc)
        logger.warning(
            f'TTS failure detected. Activating cooldown. '
            f'Last failure set to: {_tts_last_failure_timestamp}',
        )


async def reset_tts_cooldown_if_passed():
    async with _tts_cooldown_lock:
        global _tts_last_failure_timestamp
        if _tts_last_failure_timestamp and (
            (
                datetime.now(timezone.utc) - _tts_last_failure_timestamp
            ).total_seconds()
            >= TTS_COOLDOWN_SECONDS
        ):
            logger.info(
                'TTS cooldown period has passed. '
                'Resetting failure timestamp.',
            )
            _tts_last_failure_timestamp = None


async def get_saved_audio_url(
    ogg_audio_data: bytes,
    file_storage_service: R2FileStorageService,
    bot_id: str,
    language_level: LanguageLevel,
    topic: ExerciseTopic,
) -> str:
    timestamp = int(datetime.now(timezone.utc).timestamp())
    file_name = (
        f'{bot_id}/'
        f'story_audio/'
        f'{language_level.value}/'
        f'{topic.value}/'
        f'{timestamp}.ogg'
    )

    stored_audio_url = await file_storage_service.upload_audio(
        file_data=ogg_audio_data,
        file_name=file_name,
        content_type='audio/ogg',
    )
    if stored_audio_url:
        logger.info(f'Audio uploaded to R2: {stored_audio_url}')
        return stored_audio_url
    else:
        logger.error(
            f'Failed to upload audio to R2 for file_name: {file_name}'
        )
    return ''


async def get_saved_audio_telegram_file_id(
    ogg_audio_data: bytes,
    http_client: httpx.AsyncClient,
    bot_id: str,
) -> str:
    token = settings.telegram_upload_bot_tokens.get(bot_id)
    if not token:
        logger.error(f'Failed to get bot token for {bot_id}')
        return ''

    url = f'https://api.telegram.org/bot{token}/sendVoice'
    files = {'voice': ('audio.ogg', ogg_audio_data, 'audio/ogg')}
    data = {'chat_id': settings.telegram_upload_bot_chat_id}
    try:
        response = await http_client.post(
            url, data=data, files=files, timeout=20
        )
        response.raise_for_status()
        response_json = response.json()
        if response_json.get('ok') and response_json.get('result', {}).get(
            'voice'
        ):
            file_id = response_json['result']['voice']['file_id']
            logger.info(f'Audio uploaded to Telegram, file_id: {file_id}')
            return file_id
        else:
            logger.error(
                f'Failed to get file_id from Telegram response: '
                f'{response_json}'
            )
    except httpx.HTTPStatusError as e:
        logger.error(
            f'HTTP error sending file to Telegram: '
            f'{e.response.status_code} - {e.response.text}'
        )
    except Exception as e:
        logger.error(f'Failed to send telegram file: {e}', exc_info=True)
    return ''


async def _generate_and_upload_audio(
    exercise_data: StoryComprehensionExerciseData,
    target_language: str,
    language_level: LanguageLevel,
    topic: ExerciseTopic,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
    emotion_instruction: Optional[str] = None,
) -> tuple[Optional[str], Optional[str], bool]:
    """
    Generates OGG audio from text, uploads it to R2 and Telegram.
    Returns a tuple: (audio_url, telegram_file_id, success_flag).
    success_flag is True if both audio_url and telegram_file_id are obtained.
    """
    audio_url: Optional[str] = None
    telegram_file_id: Optional[str] = None
    audio_generation_successful = False

    if not exercise_data.content_text:
        logger.warning(
            'Content text is empty for STORY_COMPREHENSION. '
            'Skipping audio generation.'
        )
        return None, None, False

    VOICE_NAMES = ['Leda', 'Enceladus']
    voice_name = random.choice(VOICE_NAMES)
    ogg_audio_data = await tts_service.text_to_speech_ogg(
        text=exercise_data.content_text,
        voice_name=voice_name,
        emotion_instruction=emotion_instruction,
    )

    if ogg_audio_data:
        r2_url = await get_saved_audio_url(
            ogg_audio_data=ogg_audio_data,
            bot_id=target_language,
            language_level=language_level,
            topic=topic,
            file_storage_service=file_storage_service,
        )
        if r2_url:
            audio_url = r2_url

        tg_file_id = await get_saved_audio_telegram_file_id(
            ogg_audio_data=ogg_audio_data,
            bot_id=target_language,
            http_client=http_client,
        )
        if tg_file_id:
            telegram_file_id = tg_file_id

        if audio_url and telegram_file_id:
            audio_generation_successful = True
        else:
            logger.error(
                f'Failed to obtain both R2 URL and Telegram File ID. '
                f'R2 URL: {audio_url}, TG File ID: {telegram_file_id}'
            )
    else:
        logger.warning(
            f'TTS generation resulted in no audio data '
            f'for STORY_COMPREHENSION. '
            f'Content: "{exercise_data.content_text[:50]}..."'
        )

    return audio_url, telegram_file_id, audio_generation_successful


async def _try_to_regenerate_audio_for_exercise(
    exercise_to_retry: Exercise,
    target_language: str,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
    exercise_repository: SQLAlchemyExerciseRepository,
) -> Tuple[bool, bool]:
    """
    Tries to regenerate and save audio for an existing exercise.
    Updates the exercise status and data in the DB.
    Returns True if successfully published, False otherwise.
    """
    tts_failed_this_attempt = False
    if not isinstance(exercise_to_retry.data, StoryComprehensionExerciseData):
        logger.warning(
            f'Cannot regenerate audio for non-story exercise '
            f'{exercise_to_retry.exercise_id}'
        )
        if exercise_to_retry.exercise_id:
            await exercise_repository.update_exercise_status_and_data(
                exercise_id=exercise_to_retry.exercise_id,
                new_status=ExerciseStatus.AUDIO_GENERATION_ERROR,
            )
        return False, tts_failed_this_attempt

    logger.info(
        f'Attempting to regenerate audio for exercise ID: '
        f'{exercise_to_retry.exercise_id}'
    )

    (
        audio_url_opt,
        telegram_file_id_opt,
        audio_generated_successfully,
    ) = await _generate_and_upload_audio(
        exercise_data=exercise_to_retry.data,
        target_language=target_language,
        language_level=exercise_to_retry.language_level,
        topic=exercise_to_retry.topic,
        tts_service=tts_service,
        file_storage_service=file_storage_service,
        http_client=http_client,
        emotion_instruction=None,
    )

    current_status = ExerciseStatus.PUBLISHED
    if audio_generated_successfully and audio_url_opt and telegram_file_id_opt:
        exercise_to_retry.data.audio_url = audio_url_opt
        exercise_to_retry.data.audio_telegram_file_id = telegram_file_id_opt
    else:
        if not audio_generated_successfully:
            tts_failed_this_attempt = True
        current_status = ExerciseStatus.AUDIO_GENERATION_ERROR
        logger.error(
            f'Audio regeneration failed for exercise '
            f'{exercise_to_retry.exercise_id}. '
            f'TTS failed: {tts_failed_this_attempt}'
        )

    if exercise_to_retry.exercise_id is not None:
        updated_exercise = (
            await exercise_repository.update_exercise_status_and_data(
                exercise_id=exercise_to_retry.exercise_id,
                new_status=current_status,
                new_data=exercise_to_retry.data,
            )
        )
        if (
            updated_exercise
            and updated_exercise.status == ExerciseStatus.PUBLISHED
        ):
            logger.info(
                f'Successfully regenerated audio and published exercise '
                f'{exercise_to_retry.exercise_id}'
            )
            return True, tts_failed_this_attempt
        else:
            logger.error(
                f'Failed to publish exercise {exercise_to_retry.exercise_id} '
                f'after audio regeneration attempt. '
                f'Final status: {current_status}'
            )
            return False, tts_failed_this_attempt
    else:
        logger.error(
            'Cannot update exercise status for exercise without ID '
            'after audio regeneration attempt.'
        )
        return False, tts_failed_this_attempt


async def _repair_broken_audio_for_exercise(
    exercise_type: ExerciseType,
    target_language: str,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
) -> Tuple[bool, bool]:
    if await is_tts_cooldown_active():
        logger.info(
            'TTS cooldown active, skipping repair attempt for broken audio.',
        )
        return False, False

    async with async_session_maker() as session:
        exercise_repository = SQLAlchemyExerciseRepository(session)
        getter = exercise_repository.get_and_lock_exercise_with_audio_error
        exercise_to_retry = await getter(
            exercise_type=exercise_type,
            target_language=target_language,
        )
        if exercise_to_retry:
            logger.info(
                f'Found exercise {exercise_to_retry.exercise_id} '
                f'to retry audio generation.'
            )
            (
                published_successfully,
                tts_failed,
            ) = await _try_to_regenerate_audio_for_exercise(
                exercise_to_retry=exercise_to_retry,
                target_language=target_language,
                tts_service=tts_service,
                file_storage_service=file_storage_service,
                http_client=http_client,
                exercise_repository=exercise_repository,
            )
            await session.commit()
            return published_successfully, tts_failed
        logger.info('No exercise found to retry audio generation.')
        return False, False


async def generate_and_save_exercise(
    user_language: str,
    target_language: str,
    exercise_type: ExerciseType,
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
) -> Tuple[bool, bool]:
    tts_failed_this_generation = False
    try:
        async with exercise_generation_semaphore:
            language_level = LanguageLevel.get_next_exercise_level(
                settings.default_language_level,
            )
            topic = ExerciseTopic.get_topic_for_generation(
                exclude_topics=EXCLUDE_TOPICS,
            )

            persona: Optional[Persona] = None
            persona_log_info = 'No persona'
            if random.random() < CHANCE_TO_GENERATE_PERSONA_FOR_TOPIC:
                persona = select_persona_for_topic(topic)
                if persona:
                    persona_log_info = (
                        f'Persona: {persona.name} (Role: {persona.role}, '
                        f'Emotion: {persona.emotion}, '
                        f'Motivation: {persona.motivation}, '
                        f'Style: {persona.communication_style})'
                    )

            generation_params_log = (
                f'Starting exercise generation: Lang: {target_language}\n'
                f'Level: {language_level.value}, Type: {exercise_type.value}\n'
                f'Topic: {topic.value}, UserLang: {user_language}\n'
                f'Persona: {persona_log_info}\n'
            )

            if exercise_type == ExerciseType.STORY_COMPREHENSION:
                (
                    repaired_and_published,
                    tts_failed_repair,
                ) = await _repair_broken_audio_for_exercise(
                    exercise_type=exercise_type,
                    target_language=target_language,
                    tts_service=tts_service,
                    file_storage_service=file_storage_service,
                    http_client=http_client,
                )
                if tts_failed_repair:
                    tts_failed_this_generation = True
                if repaired_and_published:
                    logger.info(
                        f'Successfully repaired audio for a '
                        f'STORY_COMPREHENSION exercise for {target_language}.'
                    )
                    return True, tts_failed_this_generation

            if exercise_type == ExerciseType.CHOOSE_ACCENT:
                if target_language == BotID.BG.value:
                    generator = choose_accent_generator
                    exercise, answer = await generator.generate(
                        user_language=settings.default_user_language,
                    )
                    created_by = 'scrapper'
                else:
                    logger.warning(
                        f'Skipping CHOOSE_ACCENT generation for non-BG '
                        f'language: {target_language}'
                    )
                    return False, tts_failed_this_generation
            elif (
                exercise_type == ExerciseType.STORY_COMPREHENSION
                and await is_tts_cooldown_active()
            ):
                logger.warning(
                    f'Skipping STORY_COMPREHENSION exercise generation'
                    f'(Topic: {topic.value}, '
                    f'Level: {language_level.value}) '
                    f'due to TTS cooldown.'
                )
                return False, tts_failed_this_generation
            else:
                exercise, answer = await llm_service.generate_exercise(
                    user_language=user_language,
                    target_language=target_language,
                    language_level=language_level,
                    exercise_type=exercise_type,
                    topic=topic,
                    persona=persona,
                )
                created_by = 'LLM'

                if exercise.status == ExerciseStatus.PUBLISHED and isinstance(
                    exercise.data,
                    StoryComprehensionExerciseData,
                ):
                    emotion_instruction = None
                    if persona and persona.emotion_instruction_for_tts:
                        emotion_instruction = (
                            persona.emotion_instruction_for_tts
                        )
                    (
                        audio_url_opt,
                        telegram_file_id_opt,
                        audio_generated_successfully,
                    ) = await _generate_and_upload_audio(
                        exercise_data=exercise.data,
                        target_language=target_language,
                        language_level=exercise.language_level,
                        topic=exercise.topic,
                        tts_service=tts_service,
                        file_storage_service=file_storage_service,
                        http_client=http_client,
                        emotion_instruction=emotion_instruction,
                    )

                    if (
                        audio_generated_successfully
                        and audio_url_opt
                        and telegram_file_id_opt
                    ):
                        exercise.data.audio_url = audio_url_opt
                        exercise.data.audio_telegram_file_id = (
                            telegram_file_id_opt
                        )
                    else:
                        if not audio_generated_successfully:
                            tts_failed_this_generation = True
                        exercise.status = ExerciseStatus.AUDIO_GENERATION_ERROR
                        logger.error(
                            f'Audio generation/upload failed for '
                            f'NEW exercise. Topic: {topic.value}, '
                            f'Level: {language_level.value}. '
                            f'TTS failed: {tts_failed_this_generation}'
                        )

            if exercise and answer:
                exercise_details_log = (
                    f'Generated exercise params: \n{generation_params_log}'
                    f'Generated Exercise Details:\n'
                    f'  Type: {exercise.exercise_type.value}\n'
                    f'  Language: {exercise.exercise_language}\n'
                    f'  Level: {exercise.language_level.value}\n'
                    f'  Topic: {exercise.topic.value}\n'
                    f'  Status: {exercise.status.value}\n'
                    f'  Text: {exercise.exercise_text}\n'
                    f'  Data: {exercise.data.model_dump_json(indent=2)}\n'
                    f'  Correct Answer: {answer.model_dump_json(indent=2)}'
                )
                logger.info(exercise_details_log)

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
                logger.info(
                    f'Successfully generated and saved exercise ID: '
                    f'{exercise.exercise_id} '
                    f'with status: {exercise.status.value}'
                )
                return (
                    exercise.status == ExerciseStatus.PUBLISHED,
                    tts_failed_this_generation,
                )
            else:
                logger.warning(
                    f'Skipping save for exercise type '
                    f'{exercise_type.value} for {target_language} '
                    f'as it was not generated (exercise or answer is None).'
                )
                return False, tts_failed_this_generation

    except ChooseAccentGenerationError as e:
        logger.warning(f'Failed to generate CHOOSE_ACCENT exercise: {e}')
        return False, False
    except Exception as e:
        logger.error(
            f'Error during exercise generation '
            f'and saving ('
            f'{exercise_type.value if exercise_type else "UnknownType"}): '
            f'{e}',
            exc_info=True,
        )
        return False, False


async def exercise_stock_refill(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
) -> bool:
    any_tts_failure_in_this_cycle = False
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
                        ex_type.value,
                        0,
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
                                    tts_service=tts_service,
                                    file_storage_service=file_storage_service,
                                    http_client=http_client,
                                )
                            )
            if tasks:
                logger.info(
                    f'Starting generation of {len(tasks)} '
                    f'new exercises in batch.'
                )
                results = await asyncio.gather(*tasks, return_exceptions=True)
                successful_generations = 0
                for i, result_tuple_or_exc in enumerate(results):
                    if isinstance(result_tuple_or_exc, Exception):
                        logger.warning(
                            f'Exercise generation task {i} in batch '
                            f'resulted in an error (see previous logs): '
                            f'{type(result_tuple_or_exc).__name__}'
                        )
                    elif isinstance(result_tuple_or_exc, tuple):
                        published, tts_failed = result_tuple_or_exc
                        if published:
                            successful_generations += 1
                        if tts_failed:
                            any_tts_failure_in_this_cycle = True
                    else:
                        logger.error(
                            f'Unexpected result type from '
                            f'generate_and_save_exercise: '
                            f'{type(result_tuple_or_exc)}',
                        )

                logger.info(
                    f'Finished generation batch. '
                    f'Successful: {successful_generations}/{len(tasks)}. '
                    f'TTS failures detected in this cycle: '
                    f'{any_tts_failure_in_this_cycle}',
                )

    except Exception as e:
        logger.error(
            f'Error in exercise_stock_refill main logic: {e}',
            exc_info=True,
        )
    return any_tts_failure_in_this_cycle


async def exercise_stock_refill_loop(
    llm_service: LLMService,
    choose_accent_generator: ChooseAccentGenerator,
    tts_service: GoogleTTSService,
    file_storage_service: R2FileStorageService,
    http_client: httpx.AsyncClient,
    stop_event: asyncio.Event,
):
    logger.info('Exercise stock refill worker started.')

    try:
        while not stop_event.is_set():
            logger.info('Starting exercise refill cycle...')
            await reset_tts_cooldown_if_passed()

            try:
                tts_failure_detected_in_cycle = await exercise_stock_refill(
                    llm_service=llm_service,
                    choose_accent_generator=choose_accent_generator,
                    tts_service=tts_service,
                    file_storage_service=file_storage_service,
                    http_client=http_client,
                )
                if tts_failure_detected_in_cycle:
                    await set_tts_failure_timestamp()

            except Exception as e:
                logger.error(
                    f'Exercise refill cycle failed: {e}',
                    exc_info=True,
                )

            if stop_event.is_set():
                break
            try:
                await asyncio.wait_for(
                    stop_event.wait(),
                    timeout=EXERCISE_REFILL_INTERVAL,
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
