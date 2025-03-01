from unittest.mock import MagicMock

import pytest

from app.core.entities.correct_answer import CorrectAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.repositories.correct_answer import CorrectAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user import UserRepository
from app.core.services.llm import LLMService
from app.core.value_objects.answer import SentenceConstructionAnswer
from app.core.value_objects.exercise import SentenceConstructionExerciseData


@pytest.fixture
def mock_llm_service():
    return MagicMock(spec=LLMService)


@pytest.fixture
def user():
    return User(user_id=1, telegram_id=12345, username='testuser')


@pytest.fixture
def sentence_construction_answer():
    return SentenceConstructionAnswer(sentences=['This is a test sentence.'])


@pytest.fixture
def exercise():
    return Exercise(
        exercise_id=1,
        exercise_type='sentence_construction',
        language_level='beginner',
        topic='general',
        exercise_text='Make a test sentence.',
        data=SentenceConstructionExerciseData(
            words=['this', 'is', 'a', 'test', 'sentence']
        ),
    )


@pytest.fixture
def exercise_attempt(user, exercise, sentence_construction_answer):
    return ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
    )


@pytest.fixture
def correct_answer(exercise, sentence_construction_answer):
    return CorrectAnswer(
        correct_answer_id=1,
        exercise_id=exercise.exercise_id,
        answer=sentence_construction_answer,
        created_by='test',
    )


@pytest.fixture
def mock_user_repository():
    return MagicMock(spec=UserRepository)


@pytest.fixture
def mock_exercise_repository():
    return MagicMock(spec=ExerciseRepository)


@pytest.fixture
def mock_exercise_attempt_repository():
    return MagicMock(spec=ExerciseAttemptRepository)


@pytest.fixture
def mock_correct_answer_repository():
    return MagicMock(spec=CorrectAnswerRepository)
