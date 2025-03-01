from unittest.mock import MagicMock

import pytest

from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.repositories.correct_answer import CorrectAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.repositories.user import UserRepository
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService


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


@pytest.fixture
def user_service(mock_user_repository):
    return UserService(mock_user_repository)


@pytest.fixture
def exercise_service(
    mock_exercise_repository,
    mock_exercise_attempt_repository,
    mock_correct_answer_repository,
    mock_llm_service,
):
    return ExerciseService(
        mock_exercise_repository,
        mock_exercise_attempt_repository,
        mock_correct_answer_repository,
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
    mock_exercise_repository, exercise_service, user, exercise
):
    mock_exercise_repository.get_new_exercise.return_value = exercise
    retrieved_exercise = exercise_service.get_new_exercise(
        user, exercise.language_level, exercise.exercise_type
    )
    assert retrieved_exercise == exercise
    mock_exercise_repository.get_new_exercise.assert_called_once_with(
        user, exercise.language_level, exercise.exercise_type
    )


def test_exercise_service_get_new_exercise_from_llm(
    mock_exercise_repository,
    mock_llm_service,
    exercise_service,
    user,
    exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = exercise
    mock_exercise_repository.save.return_value = exercise
    retrieved_exercise = exercise_service.get_new_exercise(
        user, exercise.language_level, exercise.exercise_type
    )
    assert retrieved_exercise == exercise
    mock_exercise_repository.get_new_exercise.assert_called_once_with(
        user, exercise.language_level, exercise.exercise_type
    )
    mock_llm_service.generate_exercise.assert_called_once_with(
        user, exercise.language_level, exercise.exercise_type
    )
    mock_exercise_repository.save.assert_called_once_with(exercise)


def test_exercise_service_get_exercise_for_repetition(
    mock_exercise_repository, exercise_service, user, exercise
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        exercise
    )
    retrieved_exercise = exercise_service.get_exercise_for_repetition(
        user, exercise.language_level, exercise.exercise_type
    )
    assert retrieved_exercise == exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_called_once_with(
        user, exercise.language_level, exercise.exercise_type
    )


def test_exercise_service_get_exercise_by_id(
    mock_exercise_repository, exercise_service, exercise
):
    mock_exercise_repository.get_by_id.return_value = exercise
    retrieved_exercise = exercise_service.get_exercise_by_id(
        exercise.exercise_id
    )
    assert retrieved_exercise == exercise
    mock_exercise_repository.get_by_id.assert_called_once_with(
        exercise.exercise_id
    )


def test_exercise_service_save_exercise(
    mock_exercise_repository, exercise_service, exercise
):
    mock_exercise_repository.save.return_value = exercise
    saved_exercise = exercise_service.save_exercise(exercise)
    assert saved_exercise == exercise
    mock_exercise_repository.save.assert_called_once_with(exercise)


def test_exercise_service_validate_exercise_attempt_correct(
    mock_llm_service,
    mock_exercise_attempt_repository,
    exercise_service,
    user,
    exercise,
    sentence_construction_answer,
):
    mock_llm_service.validate_attempt.return_value = True, 'Correct!'
    exercise.data.correct_sentences = [
        sentence_construction_answer.sentences[0]
    ]
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=True,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, exercise, sentence_construction_answer
    )
    mock_llm_service.validate_attempt.assert_called_once_with(
        user, exercise, sentence_construction_answer
    )
    assert exercise_attempt.is_correct
    assert exercise_attempt.feedback is None
    assert exercise_attempt.answer == sentence_construction_answer


def test_exercise_service_validate_exercise_attempt_llm(
    mock_llm_service,
    mock_exercise_attempt_repository,
    exercise_service,
    user,
    exercise,
    sentence_construction_answer,
):
    mock_llm_service.validate_attempt.return_value = False, 'Wrong!'
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=1,
        user_id=user.user_id,
        exercise_id=exercise.exercise_id,
        answer=sentence_construction_answer,
        is_correct=False,
        feedback='Wrong!',
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt
    exercise_attempt = exercise_service.validate_exercise_attempt(
        user, exercise, sentence_construction_answer
    )
    mock_llm_service.validate_attempt.assert_called_once_with(
        user, exercise, sentence_construction_answer
    )
    assert not exercise_attempt.is_correct
    assert exercise_attempt.feedback == 'Wrong!'


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


def test_exercise_service_add_correct_answer(
    mock_correct_answer_repository,
    exercise_service,
    exercise,
    sentence_construction_answer,
):
    exercise_service.add_correct_answer(
        exercise, sentence_construction_answer, created_by='test'
    )
    mock_correct_answer_repository.save.assert_called_once()
