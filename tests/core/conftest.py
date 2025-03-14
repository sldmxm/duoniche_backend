from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.value_objects.answer import (
    FillInTheBlankAnswer,
    SentenceConstructionAnswer,
)
from app.core.value_objects.exercise import (
    FillInTheBlankExerciseData,
    SentenceConstructionExerciseData,
)


@pytest_asyncio.fixture
def mock_user_repository() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
def mock_exercise_repository() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
def mock_exercise_attempt_repository() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
def mock_cached_answer_repository() -> AsyncMock:
    return AsyncMock()


@pytest_asyncio.fixture
def mock_llm_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def user() -> User:
    return User(
        user_id=1, telegram_id=123, username='testuser', name='Test User'
    )


@pytest.fixture
def fill_in_the_blank_exercise() -> Exercise:
    return Exercise(
        exercise_id=1,
        exercise_type='fill_in_the_blank',
        language_level='beginner',
        topic='general',
        exercise_text='Fill in the blanks.',
        data=FillInTheBlankExerciseData(
            text_with_blanks='The ___ sat on the ___.', words=['cat', 'mat']
        ),
    )


@pytest.fixture
def fill_in_the_blank_answer() -> FillInTheBlankAnswer:
    return FillInTheBlankAnswer(words=['cat', 'mat'])


@pytest.fixture
def exercise_attempt(
    user: User, fill_in_the_blank_exercise: Exercise
) -> ExerciseAttempt:
    return ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=FillInTheBlankAnswer(words=['cat', 'mat']),
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=1,
    )


@pytest.fixture
def cached_answer(
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
) -> ExerciseAnswer:
    return ExerciseAnswer(
        answer_id=1,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        created_by='LLM:user:1',
        created_at=datetime(2023, 1, 1),
    )


@pytest.fixture
def sentence_construction_answer() -> SentenceConstructionAnswer:
    return SentenceConstructionAnswer(words=['I', 'am', 'happy'])


@pytest.fixture
def sentence_construction_exercise() -> Exercise:
    return Exercise(
        exercise_id=3,
        exercise_type='sentence_construction',
        language_level='beginner',
        topic='grammar',
        exercise_text='Construct a sentence.',
        data=SentenceConstructionExerciseData(
            words=['I', 'am', 'happy'],
            correct_sentence='I am happy.',
        ),
    )
