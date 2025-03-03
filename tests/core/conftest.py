from unittest.mock import MagicMock

import pytest

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseType, LanguageLevel
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user import UserRepository
from app.core.services.llm import LLMService
from app.core.value_objects.answer import SentenceConstructionAnswer
from app.core.value_objects.exercise import (
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
)


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
def sentence_construction_exercise():
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.SENTENCE_CONSTRUCTION.value,
        language_level=LanguageLevel.BEGINNER.value,
        topic='general',
        exercise_text='Make a sentence',
        data=SentenceConstructionExerciseData(
            words=[
                'this',
                'is',
                'a',
                'test',
            ]
        ),
    )


@pytest.fixture
def multiple_choice_exercise():
    return Exercise(
        exercise_id=2,
        exercise_type=ExerciseType.MULTIPLE_CHOICE.value,
        language_level=LanguageLevel.BEGINNER.value,
        topic='grammar',
        exercise_text='Choose the correct answer',
        data=MultipleChoiceExerciseData(
            options=['option1', 'option2', 'option3']
        ),
    )


@pytest.fixture
def exercise_attempt(
    user, sentence_construction_exercise, sentence_construction_answer
):
    return ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        cached_answer_id=1,
    )


@pytest.fixture
def cached_answer(
    sentence_construction_exercise, sentence_construction_answer
):
    return CachedAnswer(
        answer_id=1,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback='Correct!',
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
def mock_cached_answer_repository():
    return MagicMock(spec=CachedAnswerRepository)
