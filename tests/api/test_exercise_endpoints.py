import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_get_new_exercise_success(
    client,
    sample_exercise_request_data,
    db_sample_exercise,
    add_db_user,
):
    """Test successful retrieval of a new exercise."""
    response = await client.post(
        '/api/v1/exercises/next/', json=sample_exercise_request_data
    )

    assert response.status_code == 200
    assert (
        response.json()['exercise']['exercise_id']
        == db_sample_exercise.exercise_id
    )


@pytest.mark.asyncio
async def test_get_new_exercise_bad_request(
    client,
    user_data,
    add_db_user,
):
    """Test validation with invalid parameters."""
    response = await client.post(
        '/api/v1/exercises/next/', json={'user_id': 'test'}
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
        '/api/v1/exercises/validate/',
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
        '/api/v1/exercises/validate/', json={**user_data}
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'exercise_id']

    response = await client.post(
        '/api/v1/exercises/validate/', json={**user_data, 'exercise_id': 1}
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer']

    response = await client.post(
        '/api/v1/exercises/validate/',
        json={'exercise_id': 1, 'answer': {'words': ['test']}},
    )
    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == [
        'body',
        'answer',
        'FillInTheBlankAnswerSchema',
        'type',
    ]


@pytest.mark.asyncio
async def test_validate_exercise_bad_request_answer_type(
    client,
    user_data,
    sample_exercise_request_data,
    db_sample_exercise,
    add_db_user,
):
    """Test validation with invalid parameters."""
    response_exercise = await client.post(
        '/api/v1/exercises/next/',
        json=sample_exercise_request_data,
    )

    exercise_json = response_exercise.json()
    response = await client.post(
        '/api/v1/exercises/validate/',
        json={
            'exercise_id': exercise_json['exercise']['exercise_id'],
            'answer': {
                'answer_type': 'FillInTheBlankAnswer',
                'test': ['test'],
            },
            'user_id': user_data['user_id'],
        },
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == [
        'body',
        'answer',
        'FillInTheBlankAnswerSchema',
        'type',
    ]
