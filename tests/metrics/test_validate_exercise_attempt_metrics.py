from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.async_task_cache import AsyncTaskCache
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData

pytestmark = pytest.mark.asyncio


@pytest.fixture
def user():
    return User(
        user_id=1,
        telegram_id='123',
        username='testuser',
        name='Test User',
        user_language='en',
        target_language='bg',
    )


@pytest.fixture
def exercise():
    return Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='bg',
        language_level=LanguageLevel.A1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='Test text with ___ blank.',
            words=['word', 'word1', 'word2', 'word3'],
        ),
    )


@pytest.fixture
def mock_exercise_repo():
    return AsyncMock(spec=ExerciseRepository)


@pytest.fixture
def mock_async_task_cache():
    return AsyncMock(spec=AsyncTaskCache)


@pytest.fixture
def mock_answer_repo():
    mock = AsyncMock(spec=ExerciseAnswerRepository)
    mock.get_all_by_user_answer = AsyncMock()
    mock.save = AsyncMock()
    mock.save.return_value = ExerciseAnswer(
        answer_id=1,
        exercise_id=1,
        answer=FillInTheBlankAnswer(words=['word']),
        is_correct=False,
        feedback='Wrong!',
        feedback_language='en',
        created_at=datetime.now(),
        created_by='LLM',
    )
    return mock


@pytest.fixture
def mock_attempt_repo():
    return AsyncMock(spec=ExerciseAttemptRepository)


@pytest.fixture
def mock_backend_exercise_metrics():
    metrics = {
        'attempts': MagicMock(),
        'attempt_time': MagicMock(),
        'validation_time': MagicMock(),
        'incorrect_attempts': MagicMock(),
    }
    with patch(
        'app.core.services.attempt_validator.BACKEND_EXERCISE_METRICS', metrics
    ):
        yield metrics


@pytest.fixture
def answer_vo():
    return FillInTheBlankAnswer(words=['word'])


@pytest.fixture
def exercise_service(
    mock_exercise_repo,
    mock_answer_repo,
    mock_attempt_repo,
    mock_llm_service,
    mock_translator,
    mock_async_task_cache,
):
    return ExerciseService(
        mock_exercise_repo,
        mock_attempt_repo,
        mock_answer_repo,
        mock_llm_service,
        mock_translator,
        mock_async_task_cache,
    )


async def test_validate_exercise_attempt_metrics(
    exercise_service: ExerciseService,
    mock_answer_repo,
    mock_attempt_repo,
    mock_llm_service,
    mock_translator,
    user,
    exercise,
    answer_vo: FillInTheBlankAnswer,
    mock_backend_exercise_metrics,
):
    # Arrange
    mock_answer_repo.get_all_by_user_answer.return_value = []
    mock_llm_service.validate_attempt.return_value = False, 'Wrong!'

    # Act
    await exercise_service.validate_exercise_attempt(
        user_id=user.user_id,
        user_language='en',
        last_exercise_at=datetime.now(timezone.utc) - timedelta(seconds=10),
        exercise=exercise,
        answer=answer_vo,
    )

    # Assert
    # Check attempts
    attempts_metric = mock_backend_exercise_metrics['attempts']
    attempts_metric.labels.assert_called_once_with(
        exercise_type=exercise.exercise_type.value,
        level=exercise.language_level.value,
    )
    attempts_metric.labels().inc.assert_called_once()

    # Check attempt_time
    attempt_time_metric = mock_backend_exercise_metrics['attempt_time']
    attempt_time_metric.labels.assert_called_once_with(
        exercise_type=exercise.exercise_type.value,
        level=exercise.language_level.value,
    )
    attempt_time_metric.labels().observe.assert_called_once()

    # Check validation_time
    validation_time_metric = mock_backend_exercise_metrics['validation_time']
    validation_time_metric.labels.assert_called_once_with(
        exercise_type=exercise.exercise_type.value,
        level=exercise.language_level.value,
    )
    validation_time_metric.labels().time.assert_called_once()

    # Check incorrect_attempts
    incorrect_attempts_metric = mock_backend_exercise_metrics[
        'incorrect_attempts'
    ]
    incorrect_attempts_metric.labels.assert_called_once_with(
        exercise_type=exercise.exercise_type.value,
        level=exercise.language_level.value,
    )
    incorrect_attempts_metric.labels().inc.assert_called_once()
