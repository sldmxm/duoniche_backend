from unittest.mock import MagicMock

import pytest

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.enums import ExerciseType, LanguageLevel
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user import UserRepository
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.value_objects.answer import (
    SentenceConstructionAnswer,
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


@pytest.fixture
def user_service(mock_user_repository):
    return UserService(mock_user_repository)


@pytest.fixture
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


def test_user_service_get_user_by_id(mock_user_repository, user_service, user):
    mock_user_repository.get_by_id.return_value = user
    retrieved_user = user_service.get_user_by_id(user.user_id)
    assert retrieved_user == user
    mock_user_repository.get_by_id.assert_called_once_with(user.user_id)


def test_user_service_get_user_by_telegram_id(
    mock_user_repository, user_service, user
):
    mock_user_repository.get_by_telegram_id.return_value = user
    retrieved_user = user_service.get_user_by_telegram_id(user.telegram_id)
    assert retrieved_user == user
    mock_user_repository.get_by_telegram_id.assert_called_once_with(
        user.telegram_id
    )


def test_user_service_save_user(mock_user_repository, user_service, user):
    mock_user_repository.save.return_value = user
    saved_user = user_service.save_user(user)
    assert saved_user == user
    mock_user_repository.save.assert_called_once_with(user)


def test_exercise_service_get_new_exercise_from_repo(
    mock_exercise_repository, exercise_service, user, multiple_choice_exercise
):
    mock_exercise_repository.get_new_exercise.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = exercise_service.get_new_exercise(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_new_exercise.assert_called_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )


def test_exercise_service_get_new_exercise_from_llm(
    mock_exercise_repository,
    mock_llm_service,
    exercise_service,
    user,
    multiple_choice_exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = multiple_choice_exercise
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    retrieved_exercise = exercise_service.get_new_exercise(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_new_exercise.assert_called_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    mock_llm_service.generate_exercise.assert_called_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    mock_exercise_repository.save.assert_called_once_with(
        multiple_choice_exercise
    )


def test_exercise_service_get_exercise_for_repetition(
    mock_exercise_repository, exercise_service, user, multiple_choice_exercise
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = exercise_service.get_exercise_for_repetition(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_called_once_with(
        user,
        multiple_choice_exercise.language_level,
        multiple_choice_exercise.exercise_type,
    )


def test_exercise_service_get_exercise_by_id(
    mock_exercise_repository, exercise_service, multiple_choice_exercise
):
    mock_exercise_repository.get_by_id.return_value = multiple_choice_exercise
    retrieved_exercise = exercise_service.get_exercise_by_id(
        multiple_choice_exercise.exercise_id
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_by_id.assert_called_once_with(
        multiple_choice_exercise.exercise_id
    )


def test_exercise_service_save_exercise(
    mock_exercise_repository, exercise_service, multiple_choice_exercise
):
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    saved_exercise = exercise_service.save_exercise(multiple_choice_exercise)
    assert saved_exercise == multiple_choice_exercise
    mock_exercise_repository.save.assert_called_once_with(
        multiple_choice_exercise
    )


def test_exercise_service_validate_exercise_attempt_correct_cached(
    mock_llm_service,
    mock_exercise_attempt_repository,
    mock_cached_answer_repository,
    exercise_service,
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
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_called_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_not_called()
    assert exercise_attempt.is_correct
    assert exercise_attempt.feedback is None
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == cached_answer.answer_id


def test_exercise_service_validate_exercise_attempt_incorrect_cached(
    mock_llm_service,
    mock_exercise_attempt_repository,
    mock_cached_answer_repository,
    exercise_service,
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
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_called_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_not_called()
    assert not exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == cached_answer.answer_id


def test_exercise_service_validate_exercise_attempt_new_correct(
    mock_llm_service,
    mock_exercise_attempt_repository,
    mock_cached_answer_repository,
    exercise_service,
    user,
    sentence_construction_exercise: Exercise,
    sentence_construction_answer: SentenceConstructionAnswer,
):
    mock_llm_service.validate_attempt.return_value = True, 'Correct!'
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback='Correct!',
        cached_answer_id=1,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    new_cached_answer = CachedAnswer(
        answer_id=1,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
        feedback='Correct!',
    )
    mock_cached_answer_repository.save.return_value = new_cached_answer
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_called_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_called_once()
    mock_cached_answer_repository.save.assert_called_once()
    assert exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Correct!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == new_cached_answer.answer_id


def test_exercise_service_validate_exercise_attempt_new_incorrect(
    mock_llm_service,
    mock_exercise_attempt_repository,
    mock_cached_answer_repository,
    exercise_service,
    user,
    sentence_construction_exercise: Exercise,
    sentence_construction_answer: SentenceConstructionAnswer,
):
    mock_llm_service.validate_attempt.return_value = False, 'Wrong!'
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        None
    )
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
        cached_answer_id=1,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    new_cached_answer = CachedAnswer(
        answer_id=1,
        exercise_id=sentence_construction_exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
    )
    mock_cached_answer_repository.save.return_value = new_cached_answer
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, sentence_construction_exercise, sentence_construction_answer
    )
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_called_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )
    mock_llm_service.validate_attempt.assert_called_once()
    mock_cached_answer_repository.save.assert_called_once()
    assert not exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Wrong!'
    assert exercise_attempt.answer == sentence_construction_answer
    assert exercise_attempt.cached_answer_id == new_cached_answer.answer_id


def test_exercise_service_save_exercise_attempt(
    mock_exercise_attempt_repository, exercise_service, exercise_attempt
):
    mock_exercise_attempt_repository.save.return_value = exercise_attempt
    saved_exercise_attempt = exercise_service.save_exercise_attempt(
        exercise_attempt
    )
    assert saved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.save.assert_called_once_with(
        exercise_attempt
    )


def test_get_new_exercise_with_llm_generation(
    exercise_service,
    mock_exercise_repository,
    mock_llm_service,
    user,
    sentence_construction_exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = (
        sentence_construction_exercise
    )

    exercise = exercise_service.get_new_exercise(
        user,
        LanguageLevel.BEGINNER.value,
        ExerciseType.SENTENCE_CONSTRUCTION.value,
    )

    assert exercise == sentence_construction_exercise
    mock_llm_service.generate_exercise.assert_called_once()
    mock_exercise_repository.save.assert_called_once_with(
        sentence_construction_exercise
    )
