from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import FillInTheBlankAnswer

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
def exercise_service(
    mock_exercise_repository: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
    mock_llm_service: AsyncMock,
) -> ExerciseService:
    return ExerciseService(
        mock_exercise_repository,
        mock_exercise_attempt_repository,
        mock_exercise_answer_repository,
        mock_llm_service,
    )


async def test_get_or_create_new_exercise_from_repo(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
):
    mock_exercise_repository.get_new_exercise.return_value = (
        fill_in_the_blank_exercise
    )

    exercise = await exercise_service.get_or_create_new_exercise(
        user, 'beginner', ExerciseType.FILL_IN_THE_BLANK.value
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_new_exercise.assert_awaited_once_with(
        user=user,
        language_level='beginner',
        topic='general',
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
    )
    mock_exercise_repository.save.assert_not_awaited()


async def test_get_or_create_new_exercise_from_llm(
    mock_exercise_repository: AsyncMock,
    mock_llm_service: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
    fill_in_the_blank_answer: FillInTheBlankAnswer,
):
    mock_exercise_repository.get_new_exercise.return_value = None
    mock_llm_service.generate_exercise.return_value = (
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
    )
    mock_exercise_repository.save.return_value = fill_in_the_blank_exercise

    exercise = await exercise_service.get_or_create_new_exercise(
        user, 'beginner', ExerciseType.FILL_IN_THE_BLANK.value
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_new_exercise.assert_awaited_once_with(
        user=user,
        language_level='beginner',
        topic='general',
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
    )
    mock_llm_service.generate_exercise.assert_awaited_once_with(
        user=user,
        language_level='beginner',
        topic='general',
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
    )
    mock_exercise_repository.save.assert_awaited_once_with(
        fill_in_the_blank_exercise
    )


async def test_get_exercise_for_repetition(
    mock_exercise_repository: AsyncMock,
    exercise_service: ExerciseService,
    user: User,
    fill_in_the_blank_exercise: Exercise,
):
    mock_exercise_repository.get_exercise_for_repetition.return_value = (
        fill_in_the_blank_exercise
    )

    exercise = await exercise_service.get_exercise_for_repetition(
        user, 'beginner', ExerciseType.FILL_IN_THE_BLANK.value
    )

    assert exercise == fill_in_the_blank_exercise
    mock_exercise_repository.get_exercise_for_repetition.assert_awaited_once_with(
        user, 'beginner', ExerciseType.FILL_IN_THE_BLANK.value
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
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
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
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=None,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=exercise_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    mock_exercise_answer_repository.save.assert_not_awaited()
    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        new_exercise_attempt
    )
    assert exercise_attempt.attempt_id is None
    assert exercise_attempt.user_id == new_exercise_attempt.user_id
    assert exercise_attempt.exercise_id == new_exercise_attempt.exercise_id
    assert exercise_attempt.answer == new_exercise_attempt.answer
    assert exercise_attempt.is_correct == new_exercise_attempt.is_correct
    assert exercise_attempt.feedback == new_exercise_attempt.feedback
    assert (
        exercise_attempt.exercise_answer_id
        == new_exercise_attempt.exercise_answer_id
    )


async def test_validate_exercise_attempt_incorrect_exercise(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
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
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=None,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        exercise_answer_id=exercise_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    mock_llm_service.validate_attempt.assert_not_awaited()
    mock_exercise_answer_repository.save.assert_not_awaited()
    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        new_exercise_attempt
    )
    assert exercise_attempt.attempt_id is None
    assert exercise_attempt.user_id == new_exercise_attempt.user_id
    assert exercise_attempt.exercise_id == new_exercise_attempt.exercise_id
    assert exercise_attempt.answer == new_exercise_attempt.answer
    assert exercise_attempt.is_correct == new_exercise_attempt.is_correct
    assert exercise_attempt.feedback == new_exercise_attempt.feedback
    assert (
        exercise_attempt.exercise_answer_id
        == new_exercise_attempt.exercise_answer_id
    )


@pytest.mark.asyncio
async def test_validate_exercise_attempt_new_correct(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
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
    mock_ex_ans_repo = mock_exercise_answer_repository
    mock_exercise_answer_repository.save.return_value = new_exercise_answer
    mock_ex_ans_repo.get_correct_answers_by_exercise_id.return_value = [
        new_exercise_answer
    ]

    new_exercise_attempt = ExerciseAttempt(
        attempt_id=None,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=True,
        feedback='Correct!',
        exercise_answer_id=new_exercise_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    right_answers = [
        fill_in_the_blank_answer,
    ]
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user,
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
        right_answers,
    )
    saved_call_args = mock_exercise_answer_repository.save.await_args[0][0]
    assert saved_call_args.answer_id is None
    assert (
        saved_call_args.exercise_id == fill_in_the_blank_exercise.exercise_id
    )
    assert saved_call_args.answer == fill_in_the_blank_answer
    assert saved_call_args.is_correct
    assert saved_call_args.feedback == 'Correct!'
    assert saved_call_args.created_by == f'LLM:user:{user.user_id}'

    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        new_exercise_attempt
    )
    assert exercise_attempt.user_id == new_exercise_attempt.user_id
    assert exercise_attempt.exercise_id == new_exercise_attempt.exercise_id
    assert exercise_attempt.answer == new_exercise_attempt.answer
    assert exercise_attempt.is_correct == new_exercise_attempt.is_correct
    assert exercise_attempt.feedback == new_exercise_attempt.feedback
    assert (
        exercise_attempt.exercise_answer_id
        == new_exercise_attempt.exercise_answer_id
    )
    assert exercise_attempt == new_exercise_attempt


@pytest.mark.asyncio
async def test_validate_exercise_attempt_new_incorrect(
    mock_llm_service: AsyncMock,
    mock_exercise_attempt_repository: AsyncMock,
    mock_exercise_answer_repository: AsyncMock,
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
    new_exercise_attempt = ExerciseAttempt(
        attempt_id=None,
        user_id=user.user_id,
        exercise_id=fill_in_the_blank_exercise.exercise_id,
        answer=fill_in_the_blank_answer,
        is_correct=False,
        feedback='Wrong!',
        exercise_answer_id=new_exercise_answer.answer_id,
    )
    mock_exercise_attempt_repository.save.return_value = new_exercise_attempt

    exercise_attempt = await exercise_service.validate_exercise_attempt(
        user, fill_in_the_blank_exercise, fill_in_the_blank_answer
    )

    mock_exercise_answer_repository.get_by_exercise_and_answer.assert_awaited_once_with(
        fill_in_the_blank_exercise.exercise_id, fill_in_the_blank_answer
    )
    right_answers = []
    mock_llm_service.validate_attempt.assert_awaited_once_with(
        user,
        fill_in_the_blank_exercise,
        fill_in_the_blank_answer,
        right_answers,
    )
    saved_call_args = mock_exercise_answer_repository.save.await_args[0][0]
    assert saved_call_args.answer_id is None
    assert (
        saved_call_args.exercise_id == fill_in_the_blank_exercise.exercise_id
    )
    assert saved_call_args.answer == fill_in_the_blank_answer
    assert saved_call_args.is_correct is False
    assert saved_call_args.feedback == 'Wrong!'
    assert saved_call_args.created_by == f'LLM:user:{user.user_id}'

    mock_exercise_attempt_repository.save.assert_awaited_once_with(
        new_exercise_attempt
    )
    assert exercise_attempt.user_id == new_exercise_attempt.user_id
    assert exercise_attempt.exercise_id == new_exercise_attempt.exercise_id
    assert exercise_attempt.answer == new_exercise_attempt.answer
    assert exercise_attempt.is_correct == new_exercise_attempt.is_correct
    assert exercise_attempt.feedback == new_exercise_attempt.feedback
    assert (
        exercise_attempt.exercise_answer_id
        == new_exercise_attempt.exercise_answer_id
    )
    assert exercise_attempt == new_exercise_attempt
