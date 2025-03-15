import pytest

from app.api.dependencies import get_exercise_service
from app.core.enums import ExerciseType
from app.main import app


@pytest.mark.asyncio
async def test_get_new_exercise_success(
    mock_exercise_service,
    async_client,
    exercise_request_data,
    exercise_dict_without_type_in_data,
):
    """Test successful retrieval of a new exercise."""

    app.dependency_overrides[get_exercise_service] = mock_exercise_service

    response = await async_client.post(
        '/api/v1/exercises/new', json=exercise_request_data
    )

    assert response.status_code == 200
    assert response.json() == exercise_dict_without_type_in_data
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_new_exercise_bad_request(
    mock_exercise_service,
    async_client,
    user_data,
):
    """Test validation with invalid parameters."""
    response = await async_client.post(
        '/api/v1/exercises/new', json={**user_data}
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'language_level']

    response = await async_client.post(
        '/api/v1/exercises/new', json={**user_data, 'language_level': 'B1'}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'exercise_type']

    response = await async_client.post(
        '/api/v1/exercises/new',
        json={
            'language_level': 'B1',
            'exercise_type': ExerciseType.FILL_IN_THE_BLANK.value,
        },
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'user_id']


@pytest.mark.asyncio
async def test_validate_exercise_success(
    mock_exercise_service,
    async_client,
    validation_request_data,
    exercise_attempt,
):
    """Test successful validation of an exercise attempt."""
    app.dependency_overrides[get_exercise_service] = mock_exercise_service

    response = await async_client.post(
        '/api/v1/exercises/validate', json=validation_request_data
    )

    assert response.status_code == 200
    assert response.json() == {
        'is_correct': exercise_attempt.is_correct,
        'feedback': exercise_attempt.feedback,
    }
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validate_exercise_bad_request(
    mock_exercise_service,
    async_client,
    user_data,
):
    """Test validation with invalid parameters."""
    response = await async_client.post(
        '/api/v1/exercises/validate', json={**user_data}
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'exercise_id']

    response = await async_client.post(
        '/api/v1/exercises/validate', json={**user_data, 'exercise_id': 1}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer']

    response = await async_client.post(
        '/api/v1/exercises/validate',
        json={'exercise_id': 1, 'answer': {'words': ['test']}},
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'user_id']


@pytest.mark.asyncio
async def test_validate_exercise_bad_request_answer_type(
    mock_exercise_service,
    async_client,
    user_data,
    exercise_request_data,
):
    """Test validation with invalid parameters."""

    app.dependency_overrides[get_exercise_service] = mock_exercise_service

    response_exercise = await async_client.post(
        '/api/v1/exercises/new',
        json=exercise_request_data,
    )
    exercise_json = response_exercise.json()
    response = await async_client.post(
        '/api/v1/exercises/validate',
        json={
            'exercise_id': exercise_json['exercise_id'],
            'answer': {'test': ['test']},
            **user_data,
        },
    )
    print(f'{response.json()=}')

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer', 'words']
    app.dependency_overrides.clear()
