from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.llm.llm_service import FillInTheBlankExerciseDataParsed, LLMService

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_llm_model():
    mock = AsyncMock()
    mock.model_name = 'test-model'
    return mock


@pytest.fixture
@patch('tiktoken.encoding_for_model')
@patch.object(LLMService, '_count_tokens')
def llm_service(mock_count_tokens, mock_encoding_for_model, mock_llm_model):
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2]
    mock_encoding_for_model.return_value = mock_encoding
    mock_count_tokens.side_effect = (
        lambda text: 2 if 'Test input' in text else 10
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
    }
    with patch('app.llm.llm_service.BACKEND_LLM_METRICS', metrics):
        yield metrics


async def test_generate_exercise_metrics(
    llm_service: LLMService,
    user: User,
    mock_llm_model,
    mock_backend_llm_metrics,
):
    # Arrange
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = FillInTheBlankExerciseDataParsed(
        text_with_blanks='Test text with ___ blank.',
        right_words=['word'],
        wrong_words=['word1', 'word2', 'word3'],
    )
    llm_service._create_llm_chain = AsyncMock(return_value=mock_chain)
    exercise_type = ExerciseType.FILL_IN_THE_BLANK
    language_level = LanguageLevel.A1
    topic = ExerciseTopic.GENERAL

    # Act
    await llm_service.generate_exercise(
        user, language_level, exercise_type, topic
    )

    # Assert
    # Check exercises_created
    exercises_created_metric = mock_backend_llm_metrics['exercises_created']
    exercises_created_metric.labels.assert_called_once_with(
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
    exercises_creation_time_metric.labels.assert_called_once_with(
        exercise_type=exercise_type.value,
        level=language_level.value,
        user_language=user.user_language,
        target_language=user.target_language,
        llm_model=mock_llm_model.model_name,
    )
    exercises_creation_time_metric.labels().time.assert_called_once()

    # Check that input_tokens metric was incremented
    input_tokens_metric = mock_backend_llm_metrics['input_tokens']
    input_tokens_metric.labels().inc.assert_called_once_with(2)

    # Check that output_tokens metric was incremented
    output_tokens_metric = mock_backend_llm_metrics['output_tokens']
    output_tokens_metric.labels().inc.assert_called_once_with(2)
