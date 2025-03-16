from typing import AsyncGenerator
from unittest.mock import AsyncMock, create_autospec

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.enums import ExerciseType
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url='http://test'
    ) as ac:
        yield ac


@pytest.fixture
def exercise():
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        language_level='B1',
        topic='general',
        exercise_text='Заполни пробелы в предложении',
        data=exercise_data,
    )


@pytest.fixture
def exercise_dict_without_type_in_data(exercise):
    res = exercise.model_dump()
    res['data'].pop('type')
    return res


@pytest.fixture
def exercise_attempt():
    return ExerciseAttempt(
        attempt_id=1,
        exercise_id=1,
        user_id=1,
        answer=FillInTheBlankAnswer(words=['right']),
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=1,
    )


@pytest.fixture
def user_data():
    """Common user data for test requests."""
    return {
        'user_id': '12345',
        'telegram_id': '67890',
        'username': 'testuser',
        'name': 'Test User',
        'user_language': 'en',
        'target_language': 'fr',
    }


@pytest.fixture
def exercise_request_data(user_data):
    """Data for new exercise request."""
    return {
        **user_data,
        'language_level': 'B1',
        'exercise_type': ExerciseType.FILL_IN_THE_BLANK.value,
    }


@pytest.fixture
def validation_request_data(user_data):
    """Data for validation request."""
    return {**user_data, 'exercise_id': 1, 'answer': {'words': ['exercise']}}


@pytest_asyncio.fixture
async def mock_exercise_service(exercise, exercise_attempt):
    """Mock ExerciseService for testing."""
    service = create_autospec(ExerciseService, instance=True)

    service.get_or_create_new_exercise = AsyncMock(return_value=exercise)
    service.validate_exercise_attempt = AsyncMock(
        return_value=exercise_attempt
    )

    async def mock_generator():
        yield service

    return mock_generator
