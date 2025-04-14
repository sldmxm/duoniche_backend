from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.entities.user import User
from app.core.enums import ExerciseType, LanguageLevel
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
    mock_encoding.encode.return_value = [1, 2]
    mock_encoding_for_model.return_value = mock_encoding
    mock_count_tokens.return_value = 2
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
        'input_tokens': MagicMock(),
        'output_tokens': MagicMock(),
    }
    with patch('app.llm.llm_base.BACKEND_LLM_METRICS', metrics):
        yield metrics


async def test_run_llm_chain_token_counting(
    llm_service: LLMService,
    user: User,
    mock_llm_model,
    mock_backend_llm_metrics,
):
    # Arrange
    mock_chain = AsyncMock()
    mock_chain.ainvoke.return_value = 'Test response'
    mock_llm_model.ainvoke = mock_chain.ainvoke
    input_data = {'text': 'Test input'}
    exercise_type = ExerciseType.FILL_IN_THE_BLANK
    language_level = LanguageLevel.A1

    # Act
    await llm_service.run_llm_chain(
        chain=mock_chain,
        input_data=input_data,
        target_language=user.target_language,
        user_language=user.user_language,
        exercise_type=exercise_type,
        language_level=language_level,
    )

    # Assert
    # Check that _count_tokens was called for input and output
    assert llm_service._count_tokens('Test input') == 2
    assert llm_service._count_tokens('Test response') == 2

    # Check that input_tokens metric was incremented
    input_tokens_metric = mock_backend_llm_metrics['input_tokens']
    input_tokens_metric.labels.assert_called_once_with(
        exercise_type=exercise_type.value,
        level=language_level.value,
        user_language=user.user_language,
        target_language=user.target_language,
        llm_model=mock_llm_model.model_name,
    )
    input_tokens_metric.labels().inc.assert_called_once_with(2)

    # Check that output_tokens metric was incremented
    output_tokens_metric = mock_backend_llm_metrics['output_tokens']
    output_tokens_metric.labels.assert_called_once_with(
        exercise_type=exercise_type.value,
        level=language_level.value,
        user_language=user.user_language,
        target_language=user.target_language,
        llm_model=mock_llm_model.model_name,
    )
    output_tokens_metric.labels().inc.assert_called_once_with(2)
