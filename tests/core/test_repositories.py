from unittest.mock import AsyncMock

import pytest

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.value_objects.answer import SentenceConstructionAnswer

pytestmark = pytest.mark.asyncio


async def test_user_repository_get_by_id(
    mock_user_repository: AsyncMock, user: User
):
    mock_user_repository.get_by_id.return_value = user
    retrieved_user = await mock_user_repository.get_by_id(user.user_id)
    assert retrieved_user == user
    mock_user_repository.get_by_id.assert_awaited_once_with(user.user_id)


async def test_user_repository_get_by_telegram_id(
    mock_user_repository: AsyncMock, user: User
):
    mock_user_repository.get_by_telegram_id.return_value = user
    retrieved_user = await mock_user_repository.get_by_telegram_id(
        user.telegram_id
    )
    assert retrieved_user == user
    mock_user_repository.get_by_telegram_id.assert_awaited_once_with(
        user.telegram_id
    )


async def test_user_repository_save(
    mock_user_repository: AsyncMock, user: User
):
    mock_user_repository.save.return_value = user
    saved_user = await mock_user_repository.save(user)
    assert saved_user == user
    mock_user_repository.save.assert_awaited_once_with(user)


async def test_exercise_repository_get_by_id(
    mock_exercise_repository: AsyncMock, multiple_choice_exercise: Exercise
):
    mock_exercise_repository.get_by_id.return_value = multiple_choice_exercise
    retrieved_exercise = await mock_exercise_repository.get_by_id(
        multiple_choice_exercise.exercise_id
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_by_id.assert_awaited_once_with(
        multiple_choice_exercise.exercise_id
    )


async def test_exercise_repository_get_new_exercise(
    mock_exercise_repository: AsyncMock,
    user: User,
    multiple_choice_exercise: Exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = await mock_exercise_repository.get_new_exercise(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_new_exercise.assert_awaited_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )


async def test_exercise_repository_get_exercise_for_repetition(
    mock_exercise_repository: AsyncMock,
    user: User,
    multiple_choice_exercise: Exercise,
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = (
        await mock_exercise_repository.get_exercise_for_repetition(
            user,
            multiple_choice_exercise.language_level,
            multiple_choice_exercise.exercise_type,
        )
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_awaited_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )


async def test_exercise_repository_save(
    mock_exercise_repository: AsyncMock, multiple_choice_exercise: Exercise
):
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    saved_exercise = await mock_exercise_repository.save(
        multiple_choice_exercise
    )
    assert saved_exercise == multiple_choice_exercise
    mock_exercise_repository.save.assert_awaited_once_with(
        multiple_choice_exercise
    )


async def test_exercise_attempt_repository_get_by_id(
    mock_exercise_attempt_repository: AsyncMock,
    exercise_attempt: ExerciseAttempt,
):
    mock_exercise_attempt_repository.get_by_id.return_value = exercise_attempt
    retrieved_exercise_attempt = (
        await mock_exercise_attempt_repository.get_by_id(
            exercise_attempt.attempt_id
        )
    )
    assert retrieved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.get_by_id.assert_awaited_once_with(
        exercise_attempt.attempt_id
    )


async def test_exercise_attempt_repository_get_by_user_and_exercise(
    mock_exercise_attempt_repository: AsyncMock,
    user: User,
    multiple_choice_exercise: Exercise,
    exercise_attempt: ExerciseAttempt,
):
    mock_exercise_attempt_repository.get_by_user_and_exercise.return_value = [
        exercise_attempt
    ]
    retrieved_exercise_attempts = (
        await mock_exercise_attempt_repository.get_by_user_and_exercise(
            user.user_id, multiple_choice_exercise.exercise_id
        )
    )
    assert retrieved_exercise_attempts == [exercise_attempt]
    mock_exercise_attempt_repository.get_by_user_and_exercise.assert_awaited_once_with(
        user.user_id, multiple_choice_exercise.exercise_id
    )


async def test_exercise_attempt_repository_get_all_user_attempts(
    mock_exercise_attempt_repository: AsyncMock,
    user: User,
    exercise_attempt: ExerciseAttempt,
):
    mock_exercise_attempt_repository.get_by_user_id.return_value = [
        exercise_attempt
    ]
    retrieved_exercise_attempts = (
        await mock_exercise_attempt_repository.get_by_user_id(user.user_id)
    )
    assert retrieved_exercise_attempts == [exercise_attempt]
    mock_exercise_attempt_repository.get_by_user_id.assert_awaited_once_with(
        user.user_id
    )


async def test_exercise_attempt_repository_save(
    mock_exercise_attempt_repository: AsyncMock,
    exercise_attempt: ExerciseAttempt,
):
    mock_exercise_attempt_repository.save.return_value = exercise_attempt
    saved_exercise_attempt = await mock_exercise_attempt_repository.save(
        exercise_attempt
    )
    assert saved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        exercise_attempt
    )


async def test_cached_answer_repository_get_by_id(
    mock_cached_answer_repository: AsyncMock, cached_answer: CachedAnswer
):
    mock_cached_answer_repository.get_by_id.return_value = cached_answer
    retrieved_cached_answer = await mock_cached_answer_repository.get_by_id(
        cached_answer.answer_id
    )
    assert retrieved_cached_answer == cached_answer
    mock_cached_answer_repository.get_by_id.assert_awaited_once_with(
        cached_answer.answer_id
    )


async def test_cached_answer_repository_get_by_exercise_and_answer(
    mock_cached_answer_repository: AsyncMock,
    cached_answer: CachedAnswer,
    sentence_construction_answer: SentenceConstructionAnswer,
    sentence_construction_exercise: Exercise,
):
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        cached_answer
    )
    retrieved_cached_answer = (
        await mock_cached_answer_repository.get_by_exercise_and_answer(
            sentence_construction_exercise.exercise_id,
            sentence_construction_answer,
        )
    )
    assert retrieved_cached_answer == cached_answer
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )


async def test_cached_answer_repository_save(
    mock_cached_answer_repository: AsyncMock, cached_answer: CachedAnswer
):
    mock_cached_answer_repository.save.return_value = cached_answer
    saved_cached_answer = await mock_cached_answer_repository.save(
        cached_answer
    )
    assert saved_cached_answer == cached_answer
    mock_cached_answer_repository.save.assert_awaited_once_with(cached_answer)
