import pytest

from app.core.enums import ExerciseType


@pytest.mark.asyncio
async def test_get_new_exercise_success(
    client,
    sample_exercise_request_data,
    sample_exercise,
):
    """Test successful retrieval of a new exercise."""

    response = await client.post(
        '/api/v1/exercises/new', json=sample_exercise_request_data
    )

    assert response.status_code == 200
    assert response.json()['exercise_id'] == sample_exercise.exercise_id


@pytest.mark.asyncio
async def test_get_new_exercise_bad_request(
    client,
    user_data,
):
    """Test validation with invalid parameters."""
    response = await client.post('/api/v1/exercises/new', json={**user_data})

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'language_level']

    response = await client.post(
        '/api/v1/exercises/new', json={**user_data, 'language_level': 'B1'}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'exercise_type']

    response = await client.post(
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
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
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


@pytest.mark.asyncio
async def test_validate_exercise_bad_request_answer_type(
    client,
    user_data,
    sample_exercise_request_data,
):
    """Test validation with invalid parameters."""

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
            **user_data,
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer', 'words']
