def test_user_repository_get_by_id(mock_user_repository, user):
    mock_user_repository.get_by_id.return_value = user
    retrieved_user = mock_user_repository.get_by_id(user.user_id)
    assert retrieved_user == user
    mock_user_repository.get_by_id.assert_called_once_with(user.user_id)


def test_user_repository_get_by_telegram_id(mock_user_repository, user):
    mock_user_repository.get_by_telegram_id.return_value = user
    retrieved_user = mock_user_repository.get_by_telegram_id(user.telegram_id)
    assert retrieved_user == user
    mock_user_repository.get_by_telegram_id.assert_called_once_with(
        user.telegram_id
    )


def test_user_repository_save(mock_user_repository, user):
    mock_user_repository.save.return_value = user
    saved_user = mock_user_repository.save(user)
    assert saved_user == user
    mock_user_repository.save.assert_called_once_with(user)


def test_exercise_repository_get_by_id(
    mock_exercise_repository, multiple_choice_exercise
):
    mock_exercise_repository.get_by_id.return_value = multiple_choice_exercise
    retrieved_exercise = mock_exercise_repository.get_by_id(
        multiple_choice_exercise.exercise_id
    )
    assert retrieved_exercise == multiple_choice_exercise
    mock_exercise_repository.get_by_id.assert_called_once_with(
        multiple_choice_exercise.exercise_id
    )


def test_exercise_repository_get_new_exercise(
    mock_exercise_repository, user, multiple_choice_exercise
):
    mock_exercise_repository.get_new_exercise.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = mock_exercise_repository.get_new_exercise(
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


def test_exercise_repository_get_exercise_for_repetition(
    mock_exercise_repository, user, multiple_choice_exercise
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        multiple_choice_exercise
    )
    retrieved_exercise = mock_exercise_repository.get_exercise_for_repetition(
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


def test_exercise_repository_save(
    mock_exercise_repository, multiple_choice_exercise
):
    mock_exercise_repository.save.return_value = multiple_choice_exercise
    saved_exercise = mock_exercise_repository.save(multiple_choice_exercise)
    assert saved_exercise == multiple_choice_exercise
    mock_exercise_repository.save.assert_called_once_with(
        multiple_choice_exercise
    )


def test_exercise_attempt_repository_get_by_id(
    mock_exercise_attempt_repository, exercise_attempt
):
    mock_exercise_attempt_repository.get_by_id.return_value = exercise_attempt
    retrieved_exercise_attempt = mock_exercise_attempt_repository.get_by_id(
        exercise_attempt.attempt_id
    )
    assert retrieved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.get_by_id.assert_called_once_with(
        exercise_attempt.attempt_id
    )


def test_exercise_attempt_repository_get_by_user_and_exercise(
    mock_exercise_attempt_repository,
    user,
    multiple_choice_exercise,
    exercise_attempt,
):
    mock_exercise_attempt_repository.get_by_user_and_exercise.return_value = [
        exercise_attempt
    ]
    retrieved_exercise_attempts = (
        mock_exercise_attempt_repository.get_by_user_and_exercise(
            user.user_id, multiple_choice_exercise.exercise_id
        )
    )
    assert retrieved_exercise_attempts == [exercise_attempt]
    mock_exercise_attempt_repository.get_by_user_and_exercise.assert_called_once_with(
        user.user_id, multiple_choice_exercise.exercise_id
    )


def test_exercise_attempt_repository_get_all_user_attempts(
    mock_exercise_attempt_repository, user, exercise_attempt
):
    mock_exercise_attempt_repository.get_all_user_attempts.return_value = [
        exercise_attempt
    ]
    retrieved_exercise_attempts = (
        mock_exercise_attempt_repository.get_all_user_attempts(user.user_id)
    )
    assert retrieved_exercise_attempts == [exercise_attempt]
    mock_exercise_attempt_repository.get_all_user_attempts.assert_called_once_with(
        user.user_id
    )


def test_exercise_attempt_repository_save(
    mock_exercise_attempt_repository, exercise_attempt
):
    mock_exercise_attempt_repository.save.return_value = exercise_attempt
    saved_exercise_attempt = mock_exercise_attempt_repository.save(
        exercise_attempt
    )
    assert saved_exercise_attempt == exercise_attempt
    mock_exercise_attempt_repository.save.assert_called_once_with(
        exercise_attempt
    )


def test_cached_answer_repository_get_by_id(
    mock_cached_answer_repository, cached_answer
):
    mock_cached_answer_repository.get_by_id.return_value = cached_answer
    retrieved_cached_answer = mock_cached_answer_repository.get_by_id(
        cached_answer.answer_id
    )
    assert retrieved_cached_answer == cached_answer
    mock_cached_answer_repository.get_by_id.assert_called_once_with(
        cached_answer.answer_id
    )


def test_cached_answer_repository_get_by_exercise_and_answer(
    mock_cached_answer_repository,
    cached_answer,
    sentence_construction_answer,
    sentence_construction_exercise,
):
    mock_cached_answer_repository.get_by_exercise_and_answer.return_value = (
        cached_answer
    )
    retrieved_cached_answer = (
        mock_cached_answer_repository.get_by_exercise_and_answer(
            sentence_construction_exercise.exercise_id,
            sentence_construction_answer,
        )
    )
    assert retrieved_cached_answer == cached_answer
    mock_cached_answer_repository.get_by_exercise_and_answer.assert_called_once_with(
        sentence_construction_exercise.exercise_id,
        sentence_construction_answer,
    )


def test_cached_answer_repository_save(
    mock_cached_answer_repository, cached_answer
):
    mock_cached_answer_repository.save.return_value = cached_answer
    saved_cached_answer = mock_cached_answer_repository.save(cached_answer)
    assert saved_cached_answer == cached_answer
    mock_cached_answer_repository.save.assert_called_once_with(cached_answer)
