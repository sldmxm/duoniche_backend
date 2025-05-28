from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
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
    mock = AsyncMock(spec=AsyncTaskCache)

    async def mock_get_or_create_task(
        key, task_func, serializer, deserializer
    ):
        result = await task_func()
        return result

    mock.get_or_create_task = AsyncMock(side_effect=mock_get_or_create_task)
    return mock


@pytest.fixture
def mock_answer_repo(exercise, answer_vo):
    mock = AsyncMock(spec=ExerciseAnswerRepository)
    mock.get_all_by_user_answer = AsyncMock(return_value=[])

    def create_side_effect(exercise_answer_to_save: ExerciseAnswer):
        if exercise_answer_to_save.answer_id is None:
            exercise_answer_to_save.answer_id = 123
        return exercise_answer_to_save

    mock.create = AsyncMock(side_effect=create_side_effect)
    return mock


@pytest.fixture
def mock_attempt_repo():
    mock = AsyncMock(spec=ExerciseAttemptRepository)

    def create_side_effect(attempt_to_save):
        if attempt_to_save.attempt_id is None:
            attempt_to_save.attempt_id = 456
        return attempt_to_save

    def update_side_effect(attempt_id, **kwargs):
        updated_attempt_mock = MagicMock(spec=ExerciseAttempt)
        updated_attempt_mock.attempt_id = attempt_id
        updated_attempt_mock.is_correct = kwargs.get('is_correct')
        return updated_attempt_mock

    mock.create = AsyncMock(side_effect=create_side_effect)
    mock.update = AsyncMock(side_effect=update_side_effect)
    return mock


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
