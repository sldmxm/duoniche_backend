import logging

import pytest

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_validate_exercise_success_legacy(
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_user,
    add_user_bot_profile,
):
    """Test successful validation of an exercise attempt."""
    response = await client.post(
        '/api/v1/exercises/validate/',
        json=request_data_correct_answer_for_sample_exercise,
    )

    print(response.json())

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
    add_user_bot_profile,
):
    """Test validation with invalid parameters."""
    response = await client.post(
        '/api/v1/exercises/validate/', json={**user_data}
    )

    assert response.status_code == 422
    assert response.json()['detail'][0]['msg'] == 'Field required'
    assert response.json()['detail'][0]['loc'] == ['body', 'answer']

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
        'exercise_type',
    ]


@pytest.mark.asyncio
async def test_validate_exercise_bad_request_answer_type(
    client,
    user_data,
    user_id_for_sample_request,
    db_sample_exercise,
    add_db_user,
    add_user_bot_profile,
):
    """Test validation with invalid parameters."""
    response_exercise = await client.get(
        f"/api/v1/users/{user_data['user_id']}/next_action/",
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
        'exercise_type',
    ]


@pytest.mark.asyncio
async def test_validate_exercise_success(
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_user,
    add_user_bot_profile,
):
    """Test successful validation of an exercise attempt."""

    exercise_id = request_data_correct_answer_for_sample_exercise[
        'exercise_id'
    ]
    response = await client.post(
        f'/api/v1/exercises/{exercise_id}/validate/',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 200
    assert response.json() == {
        'is_correct': True,
        'feedback': '',
    }
