from unittest.mock import ANY, AsyncMock

import pytest
import pytest_asyncio

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.enums import ExerciseType, LanguageLevel
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.value_objects.answer import (
    SentenceConstructionAnswer,
)

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
def user_service(mock_user_repository):
    return UserService(mock_user_repository)


@pytest_asyncio.fixture
def exercise_service(
    mock_exercise_repository,
    mock_exercise_attempt_repository,
    mock_cached_answer_repository,
    mock_llm_service,
):
    return ExerciseService(
        mock_exercise_repository,
        mock_exercise_attempt_repository,
        mock_cached_answer_repository,
        mock_llm_service,
    )


async def test_user_service_get_user_by_id(
    mock_user_repository: AsyncMock, user_service: UserService, user
):
    mock_user_repository.get_by_id.return_value = user
    retrieved_user = await user_service.get_user_by_id(user.user_id)
    assert retrieved_user == user
    mock_user_repository.get_by_id.assert_awaited_once_with(user.user_id)


async def test_user_service_get_user_by_telegram_id(
    mock_user_repository: AsyncMock, user_service: UserService, user
):
    mock_user_repository.get_by_telegram_id.return_value = user
    retrieved_user = await user_service.get_user_by_telegram_id(
        user.telegram_id
    )
    assert retrieved_user == user
    mock_user_repository.get_by_telegram_id.assert_awaited_once_with(
        user.telegram_id
    )


async def test_user_service_save_user(
    mock_user_repository: AsyncMock, user_service: UserService, user
):
    mock_user_repository.save.return_value = user
    saved_user = await user_service.save_user(user)
    assert saved_user == user
    mock_user_repository.save.assert_awaited_once_with(user)


async def test_exercise_service_get_new_exercise_from_repo(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    multiple_choice_exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = await exercise_service.get_new_exercise(
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


async def test_exercise_service_get_new_exercise_from_llm(
    mock_exercise_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    exercise_service: ExerciseService,
    user,
    multiple_choice_exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = multiple_choice_exercise
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    retrieved_exercise = await exercise_service.get_new_exercise(
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
    mock_llm_service.generate_exercise.assert_awaited_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    mock_exercise_repository.save.assert_awaited_once_with(
        multiple_choice_exercise
    )


async def test_exercise_service_get_exercise_for_repetition(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    multiple_choice_exercise,
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = await exercise_service.get_exercise_for_repetition(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_awaited_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )


async def test_exercise_service_get_exercise_by_id(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    multiple_choice_exercise,
):
    mock_exercise_repository.get_by_id.return_value = multiple_choice_exercise
    retrieved_exercise = await exercise_service.get_exercise_by_id(
        multiple_choice_exercise.exercise_id
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_by_id.assert_awaited_once_with(
        multiple_choice_exercise.exercise_id
    )


async def test_exercise_service_save_exercise(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    multiple_choice_exercise,
):
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    saved_exercise = await exercise_service.save_exercise(
        multiple_choice_exercise
    )
    assert saved_exercise == multiple_choice_exercise
    mock_exercise_repository.save.assert_awaited_once_with(
        multiple_choice_exercise
    )


async def test_exercise_service_validate_exercise_attempt_correct_cached(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_cached_answer_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    sentence_construction_exercise,
    sentence_construction_answer,
):
    cached_answer = CachedAnswer(
        answer_id=1,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback=None,
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        cached_answer
    )
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback=None,
        cached_answer_id=cached_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    assert exercise_attempt.is_correct
    assert exercise_attempt.feedback is None
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == cached_answer.answer_id


async def test_exercise_service_validate_exercise_attempt_incorrect_cached(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_cached_answer_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    sentence_construction_exercise,
    sentence_construction_answer,
):
    cached_answer = CachedAnswer(
        answer_id=1,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        cached_answer
    )
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
        cached_answer_id=cached_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    assert not exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == cached_answer.answer_id


async def test_exercise_service_validate_exercise_attempt_new_correct(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_cached_answer_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    sentence_construction_exercise: Exercise,
    sentence_construction_answer: SentenceConstructionAnswer,
):
    mock_llm_service.validate_attempt.return_value = True, 'Correct!'
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_cached_answer = CachedAnswer(
        answer_id=0,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback='Correct!',
    )
    mock_cached_answer_repository.save.return_value = new_cached_answer
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback='Correct!',
        cached_answer_id=new_cached_answer.answer_id,
    )
    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.save.assert_awaited_once_with(
        CachedAnswer(
            answer_id=0,
            exercise_id=sentence_construction_exercise.exercise_id,
            answer=sentence_construction_answer,
            is_correct=True,
            feedback='Correct!',
            created_by=ANY,
        )
    )
    assert exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Correct!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == new_cached_answer.answer_id


async def test_exercise_service_validate_exercise_attempt_new_incorrect(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_cached_answer_repository: AsyncMock,
    exercise_service: ExerciseService,
    user,
    sentence_construction_exercise: Exercise,
    sentence_construction_answer: SentenceConstructionAnswer,
):
    mock_llm_service.validate_attempt.return_value = False, 'Wrong!'
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_cached_answer = CachedAnswer(
        answer_id=0,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
    )
    mock_cached_answer_repository.save.return_value = new_cached_answer
    mock_exercise_attempt_repository.save.return_value = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
        cached_answer_id=new_cached_answer.answer_id,
    )
    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.save.assert_awaited_once_with(
        CachedAnswer(
            answer_id=0,
            exercise_id=sentence_construction_exercise.exercise_id,
            answer=sentence_construction_answer,
            is_correct=False,
            feedback='Wrong!',
            created_by=ANY,
        )
    )
    assert not exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == new_cached_answer.answer_id


async def test_exercise_service_save_exercise_attempt(
    mock_exercise_attempt_repository: AsyncMock,
    exercise_service,
    exercise_attempt,
):
    mock_exercise_attempt_repository.save.return_value = exercise_attempt
    saved_exercise_attempt = await exercise_service.save_exercise_attempt(
        exercise_attempt
    )
    assert saved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        exercise_attempt
    )


async def test_get_new_exercise_with_llm_generation(
    exercise_service: ExerciseService,
    mock_exercise_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    user,
    sentence_construction_exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = (
        sentence_construction_exercise
    )
    mock_exercise_repository.save.return_value = sentence_construction_exercise

    exercise = await exercise_service.get_new_exercise(
        user,
        LanguageLevel.BEGINNER.value,
        ExerciseType.SENTENCE_CONSTRUCTION.value,
    )

    assert exercise == sentence_construction_exercise
    mock_llm_service.generate_exercise.assert_awaited_once_with(
        user,
        LanguageLevel.BEGINNER.value,
        ExerciseType.SENTENCE_CONSTRUCTION.value,
    )
    mock_exercise_repository.save.assert_awaited_once_with(
        sentence_construction_exercise
    )
