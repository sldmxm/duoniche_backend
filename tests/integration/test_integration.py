import asyncio
from unittest.mock import patch

import pytest
from sqlalchemy import text

from app.api.cache import validation_cache
from app.core.consts import DEFAULT_LANGUAGE_LEVEL
from app.core.enums import ExerciseType, LanguageLevel
from app.db.models.user import User as UserModel
from app.db.repositories.exercise_attempt import (
    SQLAlchemyExerciseAttemptRepository,
)

pytestmark = pytest.mark.asyncio(scope='function')


@patch('app.core.enums.LanguageLevel.get_new_exercise_level')
@pytest.mark.asyncio
async def test_get_new_exercise(
    mock_get_level,
    client,
    db_sample_exercise,
    sample_exercise_request_data,
    add_db_user,
):
    """Test getting a new exercise from the API."""
    mock_get_level.return_value = LanguageLevel(
        db_sample_exercise.language_level
    )
    response = await client.post(
        '/api/v1/exercises/new', json=sample_exercise_request_data
    )

    assert response.status_code == 200
    exercise_data = response.json()
    assert 'exercise_id' in exercise_data
    assert 'exercise_text' in exercise_data
    assert 'exercise_type' in exercise_data
    assert (
        exercise_data['exercise_type'] == ExerciseType.FILL_IN_THE_BLANK.value
    )
    assert exercise_data['language_level'] == db_sample_exercise.language_level


@pytest.mark.asyncio
async def test_validate_exercise_correct_with_db(
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_user,
):
    """Test validating an exercise with correct answer
    with adding correct answer into db via fixture."""
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 200
    data = response.json()
    assert 'is_correct' in data
    assert 'feedback' in data
    assert data['is_correct'] is True
    validation_cache.clear_cache()


@pytest.mark.asyncio
async def test_validate_exercise_incorrect(
    client,
    request_data_incorrect_answer_for_sample_exercise,
    db_sample_exercise,
    add_db_incorrect_exercise_answer,
    add_db_user,
):
    """Test validating an exercise with incorrect answer."""
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_incorrect_answer_for_sample_exercise,
    )

    assert response.status_code == 200
    data = response.json()
    assert 'is_correct' in data
    assert 'feedback' in data
    assert data['is_correct'] is False
    validation_cache.clear_cache()


@pytest.mark.asyncio
async def test_exercise_not_found(
    client, request_data_correct_answer_for_sample_exercise, add_db_user
):
    """Test validation with non-existent exercise ID."""
    request_data_correct_answer_for_sample_exercise['exercise_id'] = 99999

    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 404
    assert 'Exercise with ID 99999 not found' in response.json()['detail']


@patch('app.core.enums.LanguageLevel.get_new_exercise_level')
@pytest.mark.asyncio
async def test_multiple_requests_same_user(
    mock_get_level,
    client,
    user_data,
    db_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_incorrect_exercise_answer,
    request_data_correct_answer_for_sample_exercise,
    request_data_incorrect_answer_for_sample_exercise,
    add_db_user,
    async_session,
):
    """
    Test simulating a real user making a series of requests:
    1. Get a new exercise.
    2. Attempt to solve it incorrectly.
    3. Attempt to solve it correctly.
    4. Get a new exercise.
    """
    mock_get_level.return_value = LanguageLevel(
        db_sample_exercise.language_level
    )

    # 1. Get a new exercise
    new_exercise_request = user_data.get('user_id')

    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )
    assert response.status_code == 200

    # 2. Attempt to solve it incorrectly
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_incorrect_answer_for_sample_exercise,
    )
    assert response.status_code == 200
    result = response.json()
    assert result['is_correct'] is False
    assert 'feedback' in result

    # 3. Attempt to solve it correctly
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )
    assert response.status_code == 200
    result = response.json()
    assert result['is_correct'] is True
    assert 'feedback' in result

    # 3.5 New exercise
    second_exercise = db_sample_exercise

    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )

    assert response.status_code == 200
    new_exercise_data = response.json()
    assert new_exercise_data['exercise_id'] == second_exercise.exercise_id
    validation_cache.clear_cache()


@patch('app.core.enums.LanguageLevel.get_new_exercise_level')
@pytest.mark.asyncio
async def test_concurrent_requests(
    mock_get_level,
    client,
    user_data,
    db_sample_exercise,
    sample_exercise_request_data,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
    async_engine,
    async_session,
):
    """Test concurrent requests from multiple users."""
    mock_get_level.return_value = DEFAULT_LANGUAGE_LEVEL
    validation_cache.clear_cache()
    num_users = 5
    exercise_responses = []

    async def user_task(telegram_id):
        user_specific_data = {
            'telegram_id': telegram_id,
            'username': f'user_{telegram_id}',
            'name': f'User {telegram_id}',
            'user_language': 'en',
            'target_language': 'en',
        }
        db_user = UserModel(**user_specific_data)
        db_user.language_level = DEFAULT_LANGUAGE_LEVEL.value
        async_session.add(db_user)
        await async_session.commit()
        await async_session.refresh(db_user)
        await asyncio.sleep(0.1)

        try:
            response = await client.post(
                '/api/v1/exercises/new',
                json=db_user.user_id,
            )

            assert response.status_code == 200
            exercise_data = response.json()
            exercise_responses.append(exercise_data)
            await asyncio.sleep(0.05)

            validation_response = await client.post(
                '/api/v1/exercises/validate',
                json={
                    **request_data_correct_answer_for_sample_exercise,
                    'exercise_id': exercise_data['exercise_id'],
                    'user_id': db_user.user_id,
                },
            )

            assert validation_response.status_code == 200
            assert validation_response.json()['is_correct'] is True
            assert validation_response.json()['feedback'] == ''

            return exercise_data
        except Exception as e:
            print(f'Error in user_task for user {telegram_id}: {str(e)}')
            raise

    results = []
    for i in range(num_users):
        telegram_id = f'{i}'
        result = await user_task(telegram_id)
        results.append(result)
        await asyncio.sleep(0.1)

    assert len(exercise_responses) == num_users

    first_id = exercise_responses[0]['exercise_id']
    first_data_text = exercise_responses[0]['data']['text_with_blanks']
    for response in exercise_responses:
        assert response['exercise_id'] == first_id
        assert response['data']['text_with_blanks'] == first_data_text

    exercise_attempt_repository = SQLAlchemyExerciseAttemptRepository(
        async_session
    )
    exercise_attempts = await exercise_attempt_repository.get_by_exercise_id(
        exercise_id=first_id
    )

    assert len(exercise_attempts) == num_users

    user_ids_with_attempts = {attempt.user_id for attempt in exercise_attempts}
    expected_user_ids = set(range(1, num_users + 1))
    assert user_ids_with_attempts == expected_user_ids


@pytest.mark.asyncio
async def test_validation_cache_multiple_requests(
    client,
    user_data,
    db_sample_exercise,
    add_db_correct_exercise_answer,
    request_data_correct_answer_for_sample_exercise,
    add_db_user,
    async_session,
):
    """
    Test that the validation cache works correctly by making multiple
    requests with the same answer and ensuring that the LLM is only
    called once.
    """
    # Get a new exercise
    new_exercise_request = add_db_user.user_id

    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )
    assert response.status_code == 200
    exercise_data = response.json()
    exercise_id = exercise_data['exercise_id']

    # First validation request
    request_data_correct_answer_for_sample_exercise['exercise_id'] = (
        exercise_id
    )
    response1 = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )
    assert response1.status_code == 200
    result1 = response1.json()
    assert result1['is_correct'] is True
    assert 'feedback' in result1

    # Second validation request (same answer)
    response2 = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )
    assert response2.status_code == 200
    result2 = response2.json()
    assert result2['is_correct'] is True
    assert 'feedback' in result2

    # Check that the results are the same (cached)
    assert result1 == result2
    validation_cache.clear_cache()


@pytest.mark.asyncio
async def test_get_new_exercise_background_task(
    client,
    user_data,
    db_sample_exercise,
    add_db_correct_exercise_answer,
    add_db_incorrect_exercise_answer,
    request_data_correct_answer_for_sample_exercise,
    request_data_incorrect_answer_for_sample_exercise,
    add_db_user,
    async_session,
):
    """
    Test that a new exercise is generated in the background
    when the count is below the threshold.
    """
    new_exercise_request = add_db_user.user_id
    stmt = text('SELECT COUNT(*) FROM exercises')
    result = await async_session.execute(stmt)
    count = result.scalar_one()
    assert count == 1
    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )
    assert response.status_code == 200

    stmt = text('SELECT COUNT(*) FROM exercises')
    result = await async_session.execute(stmt)
    count = result.scalar_one()
    assert count == 1

    await asyncio.sleep(10)

    stmt = text('SELECT COUNT(*) FROM exercises')
    result = await async_session.execute(stmt)
    count = result.scalar_one()
    assert count > 1
