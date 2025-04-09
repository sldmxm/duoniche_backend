from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.generators.fill_in_blank_generator import (
    FillInTheBlankGenerator,
)
from app.llm.llm_base import BaseLLMService
from app.llm.llm_service import LLMService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_llm_model():
    mock = AsyncMock()
    mock.model_name = 'test-model'
    return mock


@pytest.fixture
@patch('tiktoken.encoding_for_model')
@patch.object(BaseLLMService, '_count_tokens')
def llm_service(mock_count_tokens, mock_encoding_for_model, mock_llm_model):
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3, 4, 5]
    mock_encoding_for_model.return_value = mock_encoding

    mock_count_tokens.side_effect = (
        lambda text: 2 if isinstance(text, dict) else 5
    )

    service = LLMService(openai_api_key='test-key', model_name='test-model')
    service.model = mock_llm_model
    return service


@pytest.fixture
def user():
    return User(
        user_id=1,
        telegram_id='123',
        username='testuser',
        name='Test User',
        user_language='en',
        target_language='bg',
    )


@pytest.fixture
def mock_backend_llm_metrics():
    metrics = {
        'exercises_created': MagicMock(),
        'exercises_creation_time': MagicMock(),
        'input_tokens': MagicMock(),
        'output_tokens': MagicMock(),
        'exercises_verified': MagicMock(),
        'verification_time': MagicMock(),
    }
    with patch('app.llm.llm_service.BACKEND_LLM_METRICS', metrics):
        yield metrics


@pytest.fixture
def mock_exercise_and_answer():
    exercise = Exercise(
        exercise_id=None,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='bg',
        language_level=LanguageLevel.A1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='Test text with ___ blank.',
            words=['word', 'word1', 'word2', 'word3'],
        ),
    )
    answer = FillInTheBlankAnswer(words=['word'])
    return exercise, answer


@patch.object(FillInTheBlankGenerator, 'generate')
async def test_generate_exercise_metrics(
    mock_generate,
    llm_service: LLMService,
    user: User,
    mock_llm_model,
    mock_backend_llm_metrics,
    mock_exercise_and_answer,
):
    """Тестирует запись метрик при генерации упражнения."""
    # Arrange
    exercise_type = ExerciseType.FILL_IN_THE_BLANK
    language_level = LanguageLevel.A1
    topic = ExerciseTopic.GENERAL

    # Устанавливаем мок для метода generate генератора упражнений
    mock_generate.return_value = mock_exercise_and_answer

    # Act
    await llm_service.generate_exercise(
        user, language_level, exercise_type, topic
    )

    # Assert
    # Проверяем, что был создан правильный генератор упражнений
    mock_generate.assert_called_once_with(
        user=user, language_level=language_level, topic=topic
    )

    # Check exercises_created
    exercises_created_metric = mock_backend_llm_metrics['exercises_created']
    exercises_created_metric.labels.assert_called_with(
        exercise_type=exercise_type.value,
        level=language_level.value,
        user_language=user.user_language,
        target_language=user.target_language,
        llm_model=mock_llm_model.model_name,
    )
    exercises_created_metric.labels().inc.assert_called_once()

    # Check exercises_creation_time
    exercises_creation_time_metric = mock_backend_llm_metrics[
        'exercises_creation_time'
    ]
    exercises_creation_time_metric.labels.assert_called_with(
        exercise_type=exercise_type.value,
        level=language_level.value,
        user_language=user.user_language,
        target_language=user.target_language,
        llm_model=mock_llm_model.model_name,
    )
    exercises_creation_time_metric.labels().time.assert_called_once()
