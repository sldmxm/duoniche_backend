from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio

from app.core.consts import MIN_EXERCISE_COUNT_TO_GENERATE_NEW
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import FillInTheBlankAnswer

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
def exercise_service(
    mock_exercise_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    validation_cache,
) -> ExerciseService:
    return ExerciseService(
        mock_exercise_repository,
        mock_exercise_attempt_repository,
        mock_exercise_answer_repository,
        mock_llm_service,
        validation_cache,
    )


@patch('app.core.enums.LanguageLevel.get_next_exercise_level')
async def test_get_or_create_new_exercise_from_repo(
    mock_get_level,
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
):
    """Test getting a new exercise from repo."""
    mock_get_level.return_value = LanguageLevel.B2
    mock_exercise_repository.get_new_exercise.return_value = (
        fill_in_the_blank_exercise
    )
    mock_exercise_repository.count_new_exercises.return_value = (
        MIN_EXERCISE_COUNT_TO_GENERATE_NEW + 1
    )

    exercise = await exercise_service.get_or_create_next_exercise(
        user,
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_new_exercise.assert_awaited_once_with(
        user=user,
        language_level=LanguageLevel.B2,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        topic=ExerciseTopic.GENERAL,
    )
    mock_exercise_repository.save.assert_not_awaited()


@patch('app.core.enums.LanguageLevel.get_next_exercise_level')
async def test_get_or_create_new_exercise_from_repetition(
    mock_get_level,
    mock_exercise_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    """Abstract situation - we have exercises in DB, but can't get it,
    so we generate new"""
    mock_get_level.return_value = user.language_level
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_exercise_repository.count_new_exercises.return_value = (
        MIN_EXERCISE_COUNT_TO_GENERATE_NEW + 1
    )
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        fill_in_the_blank_exercise
    )

    exercise = await exercise_service.get_or_create_next_exercise(
        user,
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_new_exercise.assert_awaited_once_with(
        user=user,
        language_level=user.language_level,
        topic=ExerciseTopic.GENERAL,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
    )
    mock_exercise_repository.get_exercise_for_repetition.assert_awaited_once_with(
        user=user,
    )


@patch('app.core.enums.LanguageLevel.get_next_exercise_level')
async def test_get_or_create_new_exercise_generate_in_background(
    mock_get_level,
    mock_exercise_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    """Test that a new exercise is generated in the background
    when the count is below the threshold."""
    mock_get_level.return_value = LanguageLevel.B1
    mock_exercise_repository.get_new_exercise.return_value = (
        fill_in_the_blank_exercise
    )
    mock_exercise_repository.count_new_exercises.return_value = (
        MIN_EXERCISE_COUNT_TO_GENERATE_NEW - 1
    )
    mock_llm_service.generate_exercise.return_value = (
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
    )
    mock_exercise_repository.save.return_value = fill_in_the_blank_exercise

    with patch('asyncio.create_task') as mock_create_task:
        exercise = await exercise_service.get_or_create_next_exercise(
            user,
        )
        assert exercise == fill_in_the_blank_exercise

        mock_create_task.assert_called_once()
        args, _ = mock_create_task.call_args
        assert args[0].__name__ == 'generate_and_save_new_exercise'

        mock_exercise_repository.count_new_exercises.assert_awaited_once_with(
            user=user,
            language_level=LanguageLevel.B1,
        )


async def test_get_exercise_for_repetition(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    redis,
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        fill_in_the_blank_exercise
    )

    exercise = await exercise_service.get_exercise_for_repetition(
        user,
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_awaited_once_with(
        user,
    )


async def test_get_exercise_by_id(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    fill_in_the_blank_exercise: Exercise,
):
    mock_exercise_repository.get_by_id.return_value = (
        fill_in_the_blank_exercise
    )

    exercise = await exercise_service.get_exercise_by_id(
        fill_in_the_blank_exercise.exercise_id
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_by_id.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id
    )


async def test_validate_exercise_attempt_correct_exercise(
    mock_llm_service: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    exercise_answer = ExerciseAnswer(
        answer_id=1,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        created_by=f'LLM:user:{user.user_id}',
        created_at=datetime(2023, 1, 1),
    )
    mock_exercise_answer_repository.get_by_exercise_and_answer.return_value = (
        exercise_answer
    )
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=1,
    )

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    mock_exercise_attempt_repository.save.assert_awaited_once()
    assert exercise_attempt.is_correct is True
    assert exercise_attempt.feedback == 'Correct!'
    assert exercise_attempt.exercise_answer_id == 1


async def test_validate_exercise_attempt_incorrect_exercise(
    mock_llm_service: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    exercise_answer = ExerciseAnswer(
        answer_id=1,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        created_by=f'LLM:user:{user.user_id}',
        created_at=datetime(2023, 1, 1),
    )
    mock_exercise_answer_repository.get_by_exercise_and_answer.return_value = (
        exercise_answer
    )
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        exercise_answer_id=1,
    )

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    mock_exercise_attempt_repository.save.assert_awaited_once()
    assert exercise_attempt.is_correct is False
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.exercise_answer_id == 1


@pytest.mark.asyncio
async def test_validate_exercise_attempt_new_correct(
    mock_llm_service: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    mock_llm_service.validate_attempt.return_value = True, 'Correct!'
    mock_exercise_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_exercise_answer = ExerciseAnswer(
        answer_id=1,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        created_by=f'LLM:user:{user.user_id}',
        created_at=datetime.now(),
    )
    mock_exercise_answer_repository.save.return_value = new_exercise_answer
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=None,
        feedback=None,
        exercise_answer_id=None,
    )
    mock_exercise_attempt_repository.update.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=1,
    )

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user,
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
    )
    mock_exercise_attempt_repository.save.assert_awaited_once()
    mock_exercise_attempt_repository.update.assert_awaited_once()
    assert exercise_attempt.is_correct is True
    assert exercise_attempt.feedback == 'Correct!'
    assert exercise_attempt.exercise_answer_id == 1


@pytest.mark.asyncio
async def test_validate_exercise_attempt_new_incorrect(
    mock_llm_service: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    mock_llm_service.validate_attempt.return_value = False, 'Wrong!'
    mock_exercise_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_exercise_answer = ExerciseAnswer(
        answer_id=1,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        created_by=f'LLM:user:{user.user_id}',
        created_at=datetime.now(),
    )
    mock_exercise_answer_repository.save.return_value = new_exercise_answer
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=None,
        feedback=None,
        exercise_answer_id=None,
    )
    mock_exercise_attempt_repository.update.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        exercise_answer_id=1,
    )

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user,
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
    )
    mock_exercise_attempt_repository.save.assert_awaited_once()
    mock_exercise_attempt_repository.update.assert_awaited_once()
    assert exercise_attempt.is_correct is False
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.exercise_answer_id == 1
