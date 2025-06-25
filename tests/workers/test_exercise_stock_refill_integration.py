from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.config import settings
from app.core.configs.enums import (
    ExerciseStatus,
    ExerciseType,
    LanguageLevel,
)
from app.core.configs.generation.config import ExerciseTopic
from app.core.value_objects.exercise import (
    ChooseAccentExerciseData,
    StoryComprehensionExerciseData,
)
from app.db.models.exercise import (
    Exercise as ExerciseModel,
)
from app.db.repositories.exercise import SQLAlchemyExerciseRepository
from app.workers.exercise_stock_refill import (
    exercise_stock_refill,
    generate_and_save_exercise,
)

pytest_plugins = ('pytest_asyncio',)


async def get_exercise_from_db(exercise_id: int, db_session):
    repo = SQLAlchemyExerciseRepository(db_session)
    return await repo.get_by_id(exercise_id)


@pytest.mark.asyncio
async def test_generate_story_comprehension_successful_first_try(
    db_session,
    mock_llm_service_for_story_and_accent,
    mock_tts_service,
    mock_file_storage_service,
    mock_http_client_telegram,
    mock_language_config_service,
):
    with patch(
        'app.workers.exercise_stock_refill.async_session_maker'
    ) as mock_session_maker:
        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__.return_value = db_session
        mock_session_scope.__aexit__.return_value = None
        mock_session_maker.return_value = mock_session_scope

        result_tuple = await generate_and_save_exercise(
            user_language=settings.default_user_language,
            target_language='Bulgarian',
            exercise_type=ExerciseType.STORY_COMPREHENSION,
            llm_service=mock_llm_service_for_story_and_accent,
            tts_service=mock_tts_service,
            file_storage_service=mock_file_storage_service,
            http_client=mock_http_client_telegram,
            language_config_service=mock_language_config_service,
        )

    assert result_tuple == (
        True,
        False,
    )
    mock_llm_service_for_story_and_accent.generate_exercise.assert_called_once()
    mock_tts_service.text_to_speech_ogg.assert_called_once()
    mock_file_storage_service.upload_audio.assert_called_once()
    mock_http_client_telegram.post.assert_called_once()

    repo = SQLAlchemyExerciseRepository(db_session)
    result = await db_session.execute(
        select(ExerciseModel)
        .order_by(ExerciseModel.exercise_id.desc())
        .limit(1)
    )
    created_exercise_model = result.scalar_one_or_none()

    assert created_exercise_model is not None
    assert created_exercise_model.status == ExerciseStatus.PUBLISHED
    assert (
        created_exercise_model.exercise_type
        == ExerciseType.STORY_COMPREHENSION.value
    )

    exercise_entity = await repo._to_entity(created_exercise_model)
    assert isinstance(exercise_entity.data, StoryComprehensionExerciseData)
    assert exercise_entity.data.audio_url == 'http://fake-r2-url.com/audio.ogg'
    assert (
        exercise_entity.data.audio_telegram_file_id == 'fake_telegram_file_id'
    )
    assert exercise_entity.data.content_text == 'This is a test story.'


@pytest.mark.asyncio
async def test_generate_story_comprehension_tts_fails(
    db_session,
    mock_llm_service_for_story_and_accent,
    mock_tts_service,
    mock_file_storage_service,
    mock_http_client_telegram,
    mock_language_config_service,
):
    mock_tts_service.text_to_speech_ogg = AsyncMock(return_value=None)

    with patch(
        'app.workers.exercise_stock_refill.async_session_maker'
    ) as mock_session_maker:
        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__.return_value = db_session
        mock_session_scope.__aexit__.return_value = None
        mock_session_maker.return_value = mock_session_scope

        result_tuple = await generate_and_save_exercise(
            user_language=settings.default_user_language,
            target_language='Bulgarian',
            exercise_type=ExerciseType.STORY_COMPREHENSION,
            llm_service=mock_llm_service_for_story_and_accent,
            tts_service=mock_tts_service,
            file_storage_service=mock_file_storage_service,
            http_client=mock_http_client_telegram,
            language_config_service=mock_language_config_service,
        )

    assert result_tuple == (
        False,
        True,
    )
    mock_llm_service_for_story_and_accent.generate_exercise.assert_called_once()
    mock_tts_service.text_to_speech_ogg.assert_called_once()
    mock_file_storage_service.upload_audio.assert_not_called()
    mock_http_client_telegram.post.assert_not_called()

    repo = SQLAlchemyExerciseRepository(db_session)
    result = await db_session.execute(
        select(ExerciseModel)
        .order_by(ExerciseModel.exercise_id.desc())
        .limit(1)
    )
    created_exercise_model = result.scalar_one_or_none()

    assert created_exercise_model is not None
    assert (
        created_exercise_model.status == ExerciseStatus.AUDIO_GENERATION_ERROR
    )
    exercise_entity = await repo._to_entity(created_exercise_model)
    assert isinstance(exercise_entity.data, StoryComprehensionExerciseData)
    assert not exercise_entity.data.audio_url
    assert not exercise_entity.data.audio_telegram_file_id


@pytest.mark.asyncio
async def test_generate_story_comprehension_repair_successful(
    db_session,
    mock_llm_service_for_story_and_accent,
    mock_tts_service,
    mock_file_storage_service,
    mock_http_client_telegram,
    mock_language_config_service,
):
    repo = SQLAlchemyExerciseRepository(db_session)
    initial_data = StoryComprehensionExerciseData(
        content_text='Story to be repaired.',
        audio_url='',
        audio_telegram_file_id='',
        options=['A', 'B', 'C'],
    )
    broken_exercise_entity = await repo._to_entity(
        ExerciseModel(
            exercise_id=1,
            exercise_type=ExerciseType.STORY_COMPREHENSION.value,
            exercise_language='Bulgarian',
            language_level=LanguageLevel.A1.value,
            topic=ExerciseTopic.GENERAL.value,
            exercise_text='Test exercise text',
            status=ExerciseStatus.AUDIO_GENERATION_ERROR.value,
            data=initial_data.model_dump(),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db_model_to_create = await repo._to_db_model(broken_exercise_entity)
    db_session.add(db_model_to_create)
    await db_session.commit()
    await db_session.refresh(db_model_to_create)

    broken_exercise_id = db_model_to_create.exercise_id
    assert broken_exercise_id is not None

    mock_llm_service_for_story_and_accent.reset_mock()
    mock_tts_service.reset_mock()
    mock_file_storage_service.reset_mock()
    mock_http_client_telegram.reset_mock()
    mock_tts_service.text_to_speech_ogg = AsyncMock(
        return_value=b'fake_ogg_data'
    )

    with patch(
        'app.workers.exercise_stock_refill.async_session_maker'
    ) as mock_session_maker:
        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__.return_value = db_session
        mock_session_scope.__aexit__.return_value = None
        mock_session_maker.return_value = mock_session_scope

        result_tuple = await generate_and_save_exercise(
            user_language=settings.default_user_language,
            target_language='Bulgarian',
            exercise_type=ExerciseType.STORY_COMPREHENSION,
            llm_service=mock_llm_service_for_story_and_accent,
            tts_service=mock_tts_service,
            file_storage_service=mock_file_storage_service,
            http_client=mock_http_client_telegram,
            language_config_service=mock_language_config_service,
        )

    assert result_tuple == (
        True,
        False,
    )
    mock_llm_service_for_story_and_accent.generate_exercise.assert_not_called()
    mock_tts_service.text_to_speech_ogg.assert_called_once()
    mock_file_storage_service.upload_audio.assert_called_once()
    mock_http_client_telegram.post.assert_called_once()

    repaired_exercise_model = await db_session.get(
        ExerciseModel, broken_exercise_id
    )  # Получаем модель из БД
    assert repaired_exercise_model is not None
    assert repaired_exercise_model.status == ExerciseStatus.PUBLISHED.value

    repaired_exercise_entity = await repo._to_entity(repaired_exercise_model)
    assert isinstance(
        repaired_exercise_entity.data, StoryComprehensionExerciseData
    )
    assert (
        repaired_exercise_entity.data.audio_url
        == 'http://fake-r2-url.com/audio.ogg'
    )
    assert (
        repaired_exercise_entity.data.audio_telegram_file_id
        == 'fake_telegram_file_id'
    )
    assert (
        repaired_exercise_entity.data.content_text == 'Story to be repaired.'
    )


@pytest.mark.asyncio
async def test_generate_choose_accent_successful(
    db_session,
    mock_llm_service_for_story_and_accent,  # Используем обновленную фикстуру
    mock_tts_service,
    mock_file_storage_service,
    mock_http_client_telegram,
    mock_language_config_service,
):
    """Тестирует успешную генерацию Choose Accent через LLMService."""
    with patch(
        'app.workers.exercise_stock_refill.async_session_maker'
    ) as mock_session_maker:
        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__.return_value = db_session
        mock_session_scope.__aexit__.return_value = None
        mock_session_maker.return_value = mock_session_scope

        result_tuple = await generate_and_save_exercise(
            user_language=settings.default_user_language,
            target_language='Bulgarian',
            exercise_type=ExerciseType.CHOOSE_ACCENT,
            llm_service=mock_llm_service_for_story_and_accent,
            tts_service=mock_tts_service,
            file_storage_service=mock_file_storage_service,
            http_client=mock_http_client_telegram,
            language_config_service=mock_language_config_service,
        )

    assert result_tuple == (
        True,
        False,
    )
    mock_llm_service_for_story_and_accent.generate_exercise.assert_called_once()
    mock_tts_service.text_to_speech_ogg.assert_not_called()

    repo = SQLAlchemyExerciseRepository(db_session)
    result = await db_session.execute(
        select(ExerciseModel)
        .order_by(ExerciseModel.exercise_id.desc())
        .limit(1)
    )
    created_exercise_model = result.scalar_one_or_none()
    assert created_exercise_model is not None
    assert created_exercise_model.status == ExerciseStatus.PUBLISHED.value
    assert (
        created_exercise_model.exercise_type
        == ExerciseType.CHOOSE_ACCENT.value
    )

    exercise_entity = await repo._to_entity(created_exercise_model)
    assert isinstance(exercise_entity.data, ChooseAccentExerciseData)
    assert exercise_entity.data.options == ['дума̀', 'ду̀ма']  # Из мока
    assert (
        exercise_entity.data.meaning == 'Тестово значение за дума.'
    )  # Из мока


@patch(
    'app.workers.exercise_stock_refill.generate_and_save_exercise',
    new_callable=AsyncMock,
)
@pytest.mark.asyncio
async def test_exercise_stock_refill_uses_language_config(
    mock_generate_and_save,
    mock_llm_service,
    mock_tts_service,
    mock_file_storage_service,
    mock_http_client,
    db_session,
    mock_language_config_service,
):
    """
    Tests that the main refill worker loop uses the LanguageConfigService
    to decide which languages to generate exercises for.
    """
    with patch(
        'app.workers.exercise_stock_refill.async_session_maker'
    ) as mock_session_maker:
        mock_session_scope = AsyncMock()
        mock_session_scope.__aenter__.return_value = db_session
        mock_session_scope.__aexit__.return_value = None
        mock_session_maker.return_value = mock_session_scope

        await exercise_stock_refill(
            llm_service=mock_llm_service,
            tts_service=mock_tts_service,
            file_storage_service=mock_file_storage_service,
            http_client=mock_http_client,
            language_config_service=mock_language_config_service,
        )

    called_languages = {
        call.kwargs['target_language']
        for call in mock_generate_and_save.call_args_list
    }
    assert called_languages.issubset({'Bulgarian', 'Serbian'})
