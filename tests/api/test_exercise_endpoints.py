import asyncio
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.api.cache import ValidationCache
from app.core.enums import LanguageLevel
from app.core.value_objects.answer import FillInTheBlankAnswer


@patch('app.core.enums.LanguageLevel.get_new_exercise_level')
@pytest.mark.asyncio
async def test_get_new_exercise_success(
    mock_get_level,
    client,
    sample_exercise_request_data,
    db_sample_exercise,
    add_db_user,
):
    """Test successful retrieval of a new exercise."""
    mock_get_level.return_value = LanguageLevel(
        db_sample_exercise.language_level
    )
    response = await client.post(
        '/api/v1/exercises/new', json=sample_exercise_request_data
    )

    assert response.status_code == 200
    assert response.json()['exercise_id'] == db_sample_exercise.exercise_id


@pytest.mark.asyncio
async def test_get_new_exercise_bad_request(
    client,
    user_data,
    add_db_user,
):
    """Test validation with invalid parameters."""
    response = await client.post(
        '/api/v1/exercises/new', json={'user_id': 'test'}
    )
    assert response.status_code == 422
    assert (
        response.json()['detail'][0]['msg']
        == 'Input should be a valid integer'
    )
    assert response.json()['detail'][0]['loc'] == [
        'body',
    ]


@pytest.mark.asyncio
async def test_validate_exercise_success(
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_user,
):
    """Test successful validation of an exercise attempt."""
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 200
    assert response.json() == {
        'is_correct': True,
        'feedback': '',
    }


@pytest.mark.asyncio
async def test_validate_exercise_bad_request(
    client,
    user_data,
    add_db_user,
):
    """Test validation with invalid parameters."""
    response = await client.post(
        '/api/v1/exercises/validate', json={**user_data}
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'exercise_id']

    response = await client.post(
        '/api/v1/exercises/validate', json={**user_data, 'exercise_id': 1}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer']

    response = await client.post(
        '/api/v1/exercises/validate',
        json={'exercise_id': 1, 'answer': {'words': ['test']}},
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'user_id']


@patch('app.core.enums.LanguageLevel.get_new_exercise_level')
@pytest.mark.asyncio
async def test_validate_exercise_bad_request_answer_type(
    mock_get_level,
    client,
    user_data,
    sample_exercise_request_data,
    db_sample_exercise,
    add_db_user,
):
    """Test validation with invalid parameters."""
    mock_get_level.return_value = LanguageLevel(
        db_sample_exercise.language_level
    )
    response_exercise = await client.post(
        '/api/v1/exercises/new',
        json=sample_exercise_request_data,
    )

    exercise_json = response_exercise.json()
    response = await client.post(
        '/api/v1/exercises/validate',
        json={
            'exercise_id': exercise_json['exercise_id'],
            'answer': {'test': ['test']},
            'user_id': user_data['user_id'],
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer', 'words']


@pytest_asyncio.fixture
def validation_cache() -> ValidationCache:
    return ValidationCache()


@pytest.mark.asyncio
async def test_concurrent_validation_requests_single_llm_call(
    validation_cache,
    user,
    fill_in_the_blank_exercise,
):
    """Test that concurrent validation requests for the same
    incorrect answer result in a single LLM call."""
    num_requests = 5
    mock_validation_func = AsyncMock(return_value=False)
    exercise_id = fill_in_the_blank_exercise.exercise_id
    answer = FillInTheBlankAnswer(words=['wrong', 'answer'])
    cache_key = f'validation_{exercise_id}_{hash(str(answer))}'

    async def validation_task():
        return await validation_cache.get_or_create_validation(
            cache_key, mock_validation_func
        )

    tasks = [validation_task() for _ in range(num_requests)]
    results = await asyncio.gather(*tasks)

    assert all(result is False for result in results)
    assert len(results) == num_requests
    mock_validation_func.assert_awaited_once()
