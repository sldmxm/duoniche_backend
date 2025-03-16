import pytest

from app.core.enums import ExerciseType

pytestmark = pytest.mark.asyncio(scope='function')


@pytest.mark.asyncio
async def test_get_new_exercise(
    client, sample_exercise, sample_exercise_request_data
):
    """Test getting a new exercise from the API."""
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
    assert exercise_data['language_level'] == sample_exercise.language_level


@pytest.mark.asyncio
async def test_validate_exercise_correct_with_db(
    client,
    request_data_correct_answer_for_sample_exercise,
    add_db_correct_exercise_answer,
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


@pytest.mark.asyncio
async def test_validate_exercise_correct_with_llm(
    client,
    request_data_correct_answer_for_sample_exercise,
):
    """Test validating an exercise with correct answer
    without adding correct answer into db via fixture."""
    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 200
    data = response.json()
    assert 'is_correct' in data
    assert 'feedback' in data
    assert data['is_correct'] is True


@pytest.mark.asyncio
async def test_validate_exercise_incorrect(
    client,
    request_data_incorrect_answer_for_sample_exercise,
    sample_exercise,
    add_db_incorrect_exercise_answer,
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


@pytest.mark.asyncio
async def test_exercise_not_found(
    client, request_data_correct_answer_for_sample_exercise
):
    """Test validation with non-existent exercise ID."""
    request_data_correct_answer_for_sample_exercise['exercise_id'] = 99999

    response = await client.post(
        '/api/v1/exercises/validate',
        json=request_data_correct_answer_for_sample_exercise,
    )

    assert response.status_code == 404
    assert 'Exercise with ID 99999 not found' in response.json()['detail']


@pytest.mark.asyncio
async def test_multiple_requests_same_user(
    client,
    user_data,
    sample_exercise,
    add_db_correct_exercise_answer,
    add_db_incorrect_exercise_answer,
    request_data_correct_answer_for_sample_exercise,
    request_data_incorrect_answer_for_sample_exercise,
):
    """
    Test simulating a real user making a series of requests:
    1. Get a new exercise.
    2. Attempt to solve it incorrectly.
    3. Attempt to solve it correctly.
    4. Get a new exercise.
    """
    # 1. Get a new exercise (B1 level)
    new_exercise_request = {
        **user_data,
        'language_level': sample_exercise.language_level,
        'exercise_type': sample_exercise.exercise_type,
    }

    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )
    assert response.status_code == 200
    exercise_data = response.json()
    exercise_id = exercise_data['exercise_id']

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

    # 4. Get a new exercise by LLM
    response = await client.post(
        '/api/v1/exercises/new', json=new_exercise_request
    )
    assert response.status_code == 200
    new_exercise_data = response.json()
    assert new_exercise_data['exercise_id'] != exercise_id
