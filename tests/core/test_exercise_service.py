import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_answer import ExerciseAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.generation.config import ExerciseTopic
from app.core.interfaces.llm_provider import LLMProvider
from app.core.interfaces.translate_provider import TranslateProvider
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_answer import ExerciseAnswerRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.async_task_cache import AsyncTaskCache
from app.core.services.exercise import ExerciseService
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData

# --- Mocks for Dependencies ---


@pytest.fixture
def mock_exercise_repo(mocker):
    return mocker.AsyncMock(spec=ExerciseRepository)


@pytest.fixture
def mock_attempt_repo(mocker):
    mock = mocker.AsyncMock(spec=ExerciseAttemptRepository)

    # Make save return the object passed in, but with an ID
    async def _save_attempt(attempt: ExerciseAttempt) -> ExerciseAttempt:
        if attempt.attempt_id is None:
            attempt.attempt_id = 123  # Assign a dummy ID
        return attempt

    # Make update return an updated object
    async def _update_attempt(attempt_id, **kwargs) -> ExerciseAttempt:
        # Create a dummy base attempt to update
        base_attempt = ExerciseAttempt(
            attempt_id=attempt_id,
            user_id=1,
            exercise_id=101,
            answer=Answer(),
            is_correct=None,  # Initial state before update
            feedback=None,
            answer_id=None,
        )
        # Apply updates
        for key, value in kwargs.items():
            if hasattr(base_attempt, key):
                setattr(base_attempt, key, value)
        return base_attempt

    mock.create.side_effect = _save_attempt
    mock.update.side_effect = _update_attempt
    return mock


@pytest.fixture
def mock_answer_repo(mocker):
    mock = mocker.AsyncMock(spec=ExerciseAnswerRepository)

    # Make save return the object passed in, potentially with an ID
    async def _save_answer(answer: ExerciseAnswer) -> ExerciseAnswer:
        if answer.answer_id is None:
            answer.answer_id = 500 + hash(
                answer.answer.get_answer_text()
            )  # Assign a semi-unique dummy ID
        return answer

    mock.create.side_effect = _save_answer
    mock.get_all_by_user_answer.return_value = []
    return mock


@pytest.fixture
def mock_llm_service(mocker):
    mock = mocker.AsyncMock(spec=LLMProvider)
    # Default mock behavior for validate_attempt
    mock.validate_attempt.return_value = (False, 'Default LLM Feedback')
    return mock


@pytest.fixture
def mock_translator(mocker):
    mock = mocker.AsyncMock(spec=TranslateProvider)

    # Default mock behavior for translate_text
    async def _translate_text(text, target_language):
        return f'Translated to {target_language}: {text}'

    async def _translate_feedback(
        feedback: str,
        user_language: str,
        exercise_data: str,
        user_answer: str,
        exercise_language: str,
    ):
        return f'Translated to {user_language}: {feedback}'

    mock.translate_text.side_effect = _translate_text
    mock.translate_feedback.side_effect = _translate_feedback
    return mock


@pytest_asyncio.fixture
async def async_task_cache(mocker, redis) -> AsyncTaskCache:
    cache = AsyncTaskCache(redis)
    yield cache


# --- Service Instance Fixture ---


@pytest.fixture
def exercise_service(
    mock_exercise_repo,
    mock_attempt_repo,
    mock_answer_repo,
    mock_llm_service,
    mock_translator,
    async_task_cache,
) -> ExerciseService:
    """Provides an ExerciseService instance with mocked dependencies."""
    return ExerciseService(
        exercise_repository=mock_exercise_repo,
        exercise_attempt_repository=mock_attempt_repo,
        exercise_answers_repository=mock_answer_repo,
        llm_service=mock_llm_service,
        translator=mock_translator,
        async_task_cache=async_task_cache,
    )


@pytest.fixture
def exercise() -> Exercise:
    # Assuming Exercise requires at least exercise_id for validation context
    exercise_data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test ____ for learning.',
        words=['exercise'],
    )
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level=settings.default_language_level.value,
        topic=ExerciseTopic.GENERAL.value,
        exercise_text='Fill in the blank in the sentence.',
        data=exercise_data,
    )
    return exercise


@pytest.fixture
def answer_vo() -> Answer:
    # Assuming Answer has a way to get its text content
    return FillInTheBlankAnswer(words=['user', 'answer'])


@pytest.fixture
def db_answer_correct(exercise, answer_vo) -> ExerciseAnswer:
    return ExerciseAnswer(
        answer_id=501,
        exercise_id=exercise.exercise_id,
        answer=answer_vo,  # Answer matches user's input
        is_correct=True,
        feedback='Correct!',
        feedback_language='en',  # Matches default user language
        created_at=datetime.now(),
        created_by='LLM',
    )


@pytest.fixture
def db_answer_wrong_lang(exercise, answer_vo, user) -> ExerciseAnswer:
    # Assume user language is 'en' (from user fixture)
    other_lang = 'fr'
    return ExerciseAnswer(
        answer_id=502,
        exercise_id=exercise.exercise_id,
        answer=answer_vo,  # Answer matches user's input
        is_correct=False,  # Not necessarily correct
        feedback='Feedback en français',
        feedback_language=other_lang,  # Different language
        created_at=datetime.now(),
        created_by='LLM',
    )


@pytest.fixture
def validated_answer(
    exercise, answer_vo, user, user_bot_profile
) -> ExerciseAnswer:
    # Represents an answer generated *by* the LLM validation process
    return ExerciseAnswer(
        answer_id=503,  # Should get assigned by mock save
        exercise_id=exercise.exercise_id,
        answer=answer_vo,  # Matches the answer being validated
        is_correct=False,
        feedback='LLM says this is incorrect.',
        # LLM provides in user's language
        feedback_language=user_bot_profile.user_language,
        created_at=datetime.now(),
        created_by=f'LLM:user:{user.user_id}',
    )


@pytest.fixture
def translated_answer(
    db_answer_wrong_lang, user_bot_profile
) -> ExerciseAnswer:
    return ExerciseAnswer(
        answer_id=504,
        exercise_id=db_answer_wrong_lang.exercise_id,
        answer=db_answer_wrong_lang.answer,
        is_correct=db_answer_wrong_lang.is_correct,
        feedback=f'Translated to {user_bot_profile.user_language}:'
        f' {db_answer_wrong_lang.feedback}',
        feedback_language=user_bot_profile.user_language,
        created_at=datetime.now(),
        created_by=f'translated_answer:{db_answer_wrong_lang.answer_id}',
    )


pytestmark = pytest.mark.asyncio


class TestExerciseServiceValidation:
    async def test_validate_attempt_db_hit_correct_answer(
        self,
        exercise_service: ExerciseService,
        mock_answer_repo,
        mock_attempt_repo,
        async_task_cache,
        user: User,
        exercise: Exercise,
        answer_vo: Answer,
        db_answer_correct: ExerciseAnswer,
    ):
        """
        Scenario: An existing correct answer is found
        in the DB for the user's answer text.
        Expected: Return attempt immediately using DB data,
        no cache/LLM/translate calls.
        """
        # Arrange
        mock_answer_repo.get_all_by_user_answer.return_value = [
            db_answer_correct
        ]

        # Act
        result_attempt = await exercise_service.validate_exercise_attempt(
            user_id=user.user_id,
            exercise=exercise,
            answer=answer_vo,
            user_language='en',
            last_exercise_at=None,
        )

        # Assert
        mock_answer_repo.get_all_by_user_answer.assert_awaited_once_with(
            exercise.exercise_id, answer_vo
        )
        # Should save the attempt with data from the correct DB answer
        mock_attempt_repo.create.assert_awaited_once()
        saved_attempt_arg = mock_attempt_repo.create.call_args[0][0]
        assert saved_attempt_arg.is_correct is True
        assert saved_attempt_arg.feedback == db_answer_correct.feedback
        assert saved_attempt_arg.answer_id == db_answer_correct.answer_id
        assert saved_attempt_arg.user_id == user.user_id
        assert saved_attempt_arg.exercise_id == exercise.exercise_id
        assert saved_attempt_arg.answer == answer_vo

        # Should not update after initial save
        mock_attempt_repo.update.assert_not_called()

        assert (
            result_attempt.attempt_id is not None
        )  # Check ID was assigned by mock save
        assert result_attempt.is_correct is True
        assert result_attempt.answer_id == db_answer_correct.answer_id

    async def test_validate_attempt_db_hit_correct_language(
        self,
        exercise_service: ExerciseService,
        mock_answer_repo,
        mock_attempt_repo,
        async_task_cache,
        user: User,
        exercise: Exercise,
        answer_vo: Answer,
        # Re-use correct answer fixture but modify it
        db_answer_correct: ExerciseAnswer,
    ):
        """
        Scenario: An existing answer (not marked correct) is found in DB
                  with the correct feedback language.
        Expected: Return attempt immediately using DB data,
                    no cache/LLM/translate calls.
        """
        # Arrange
        db_answer_correct_lang = db_answer_correct.model_copy()
        db_answer_correct_lang.is_correct = False
        db_answer_correct_lang.feedback = (
            'Feedback in correct language but answer wrong.'
        )

        mock_answer_repo.get_all_by_user_answer.return_value = [
            db_answer_correct_lang
        ]

        # Act
        result_attempt = await exercise_service.validate_exercise_attempt(
            user_id=user.user_id,
            exercise=exercise,
            answer=answer_vo,
            user_language='en',
            last_exercise_at=None,
        )

        # Assert
        mock_answer_repo.get_all_by_user_answer.assert_awaited_once_with(
            exercise.exercise_id, answer_vo
        )
        # Should save the attempt with data from the correct language DB answer
        mock_attempt_repo.create.assert_awaited_once()
        saved_attempt_arg = mock_attempt_repo.create.call_args[0][0]
        assert saved_attempt_arg.is_correct is False
        assert saved_attempt_arg.feedback == db_answer_correct_lang.feedback
        assert saved_attempt_arg.answer_id == db_answer_correct_lang.answer_id

        mock_attempt_repo.update.assert_not_called()

        assert result_attempt.is_correct is False
        assert result_attempt.answer_id == db_answer_correct_lang.answer_id

    async def test_validate_attempt_db_hit_needs_translation(
        self,
        exercise_service: ExerciseService,
        mock_answer_repo,
        mock_attempt_repo,
        async_task_cache,
        mock_translator,
        user: User,
        user_bot_profile,
        exercise: Exercise,
        answer_vo: Answer,
        db_answer_wrong_lang: ExerciseAnswer,
        translated_answer: ExerciseAnswer,
    ):
        """
        Scenario: An existing answer found in DB,
                but needs translation. Cache miss.
        Expected: Save initial attempt, call cache for
                translation, update attempt.
        """
        # Arrange
        mock_answer_repo.get_all_by_user_answer.return_value = [
            db_answer_wrong_lang
        ]

        # Act
        result_attempt = await exercise_service.validate_exercise_attempt(
            user_id=user.user_id,
            exercise=exercise,
            answer=answer_vo,
            user_language='en',
            last_exercise_at=None,
        )

        # Assert
        mock_answer_repo.get_all_by_user_answer.assert_awaited_once_with(
            exercise.exercise_id, answer_vo
        )
        # 1. Initial save of the attempt (before translation)
        mock_attempt_repo.create.assert_awaited_once()
        initial_attempt_arg = mock_attempt_repo.create.call_args[0][0]
        assert initial_attempt_arg.is_correct is None  # Not determined yet
        assert initial_attempt_arg.feedback is None
        assert initial_attempt_arg.answer_id is None
        initial_attempt_id = 123  # From mock_attempt_repo.save side_effect

        # 3. Translation service call
        # (inside the task_func simulated by cache mock)
        mock_translator.translate_feedback.assert_awaited_once_with(
            feedback=db_answer_wrong_lang.feedback,
            user_language=user_bot_profile.user_language,
            exercise_data=exercise.data.model_dump_json(),
            user_answer=answer_vo.get_answer_text(),
            exercise_language=exercise.exercise_language,
        )

        # 4. Save call for the *new* translated answer
        # (inside copy_answer_with_translated_feedback)
        # Check the *second* call to answer repo save
        # (first might be in another test setup if run together)
        new_translated_answer = None
        # A better way is to check the arguments specifically
        # for the translated answer.
        found_translated_save = False
        for call_args in mock_answer_repo.create.call_args_list:
            saved_answer = call_args[0][0]
            if (
                saved_answer.created_by
                == f'translated_answer:{db_answer_wrong_lang.answer_id}'
            ):
                found_translated_save = True
                assert (
                    saved_answer.feedback == translated_answer.feedback
                )  # Check content
                new_translated_answer = saved_answer
                assert (
                    saved_answer.feedback_language
                    == user_bot_profile.user_language
                )
                break
        assert (
            found_translated_save
        ), 'Saving the translated answer did not happen as expected.'

        # 5. Update call for the initial attempt
        mock_attempt_repo.update.assert_awaited_once_with(
            attempt_id=initial_attempt_id,
            is_correct=translated_answer.is_correct,
            feedback=translated_answer.feedback,
            # Use ID from saved translated answer
            answer_id=new_translated_answer.answer_id,
        )

        # 6. Final result check
        assert result_attempt.attempt_id == initial_attempt_id
        assert result_attempt.is_correct == translated_answer.is_correct
        assert result_attempt.feedback == translated_answer.feedback
        assert (
            result_attempt.answer_id == new_translated_answer.answer_id
        )  # ID from saved translated

    async def test_validate_attempt_db_miss_needs_validation(
        self,
        exercise_service: ExerciseService,
        mock_answer_repo,
        mock_attempt_repo,
        async_task_cache,
        mock_llm_service,
        user: User,
        exercise: Exercise,
        answer_vo: Answer,
        validated_answer: ExerciseAnswer,
        user_bot_profile,
    ):
        """
        Scenario: No relevant answer found in DB.
            Cache miss for validation.
        Expected: Save initial attempt, call cache
            for LLM validation, update attempt.
        """
        # Arrange
        mock_answer_repo.get_all_by_user_answer.return_value = []  # DB miss

        # Act
        result_attempt = await exercise_service.validate_exercise_attempt(
            user_id=user.user_id,
            exercise=exercise,
            answer=answer_vo,
            user_language='en',
            last_exercise_at=None,
        )

        # Assert
        mock_answer_repo.get_all_by_user_answer.assert_awaited_once_with(
            exercise.exercise_id, answer_vo
        )
        # 1. Initial save of the attempt (before validation)
        mock_attempt_repo.create.assert_awaited_once()
        initial_attempt_arg = mock_attempt_repo.create.call_args[0][0]
        assert initial_attempt_arg.is_correct is None
        initial_attempt_id = 123  # From mock_attempt_repo.save side_effect

        # 2. Cache call for validation
        # Check the first call (duplicate request handling)

        # 3. LLM service call (inside the task_func simulated by cache mock)
        mock_llm_service.validate_attempt.assert_awaited_once_with(
            user_language=user_bot_profile.user_language,
            exercise=exercise,
            answer=answer_vo,
        )

        # 4. Save call for the *new* validated answer
        # (inside llm_validate_and_save...)
        found_validated_save = False
        saved_answer = None
        for call_args in mock_answer_repo.create.call_args_list:
            saved_answer = call_args[0][0]
            if saved_answer.created_by == f'LLM:user:{user.user_id}':
                found_validated_save = True
                assert saved_answer.feedback == 'Default LLM Feedback'
                assert saved_answer.is_correct == validated_answer.is_correct
                break
        assert (
            found_validated_save
        ), 'Saving the validated answer did not happen as expected.'

        # 5. Update call for the initial attempt
        mock_attempt_repo.update.assert_awaited_once_with(
            attempt_id=initial_attempt_id,
            is_correct=validated_answer.is_correct,
            feedback='Default LLM Feedback',
            answer_id=saved_answer.answer_id,
        )

        # 6. Final result check
        assert result_attempt.attempt_id == initial_attempt_id
        assert result_attempt.is_correct == validated_answer.is_correct
        assert result_attempt.feedback == 'Default LLM Feedback'
        assert result_attempt.answer_id == saved_answer.answer_id

    async def test_validate_attempt_duplicate_request(
        self,
        mock_llm_service: AsyncMock,
        mock_answer_repo: AsyncMock,
        mock_attempt_repo: AsyncMock,
        async_task_cache: AsyncTaskCache,
        exercise_service: ExerciseService,
        user: User,
        fill_in_the_blank_exercise: Exercise,
        fill_in_the_blank_answer: FillInTheBlankAnswer,
        user_bot_profile,
    ):
        user.user_id = 157

        mock_llm_service.validate_attempt.return_value = False, 'Wrong!'
        mock_answer_repo.get_all_by_user_answer.return_value = []
        mock_attempt_repo.create.return_value = ExerciseAttempt(
            attempt_id=1,
            user_id=user.user_id,
            exercise_id=fill_in_the_blank_exercise.exercise_id,
            answer=fill_in_the_blank_answer,
            is_correct=None,
            feedback=None,
            answer_id=None,
        )
        mock_attempt_repo.update.return_value = ExerciseAttempt(
            attempt_id=1,
            user_id=user.user_id,
            exercise_id=fill_in_the_blank_exercise.exercise_id,
            answer=fill_in_the_blank_answer,
            is_correct=False,
            feedback='Wrong!',
            answer_id=1,
        )

        # Simulate two concurrent requests
        task1 = asyncio.create_task(
            exercise_service.validate_exercise_attempt(
                user_id=user.user_id,
                exercise=fill_in_the_blank_exercise,
                answer=fill_in_the_blank_answer,
                user_language='en',
                last_exercise_at=None,
            )
        )
        task2 = asyncio.create_task(
            exercise_service.validate_exercise_attempt(
                user_id=user.user_id,
                exercise=fill_in_the_blank_exercise,
                answer=fill_in_the_blank_answer,
                user_language='en',
                last_exercise_at=None,
            )
        )

        # Wait for both tasks to complete
        exercise_attempt1, exercise_attempt2 = await asyncio.gather(
            task1, task2
        )

        # Assertions
        assert mock_answer_repo.get_all_by_user_answer.assert_awaited_once
        mock_llm_service.validate_attempt.assert_awaited_once_with(
            user_language=user_bot_profile.user_language,
            exercise=fill_in_the_blank_exercise,
            answer=fill_in_the_blank_answer,
        )
        mock_attempt_repo.create.assert_awaited_once()
        mock_attempt_repo.update.assert_awaited_once()
        assert exercise_attempt1.is_correct is False
        assert exercise_attempt1.feedback == 'Wrong!'
        assert exercise_attempt1 is exercise_attempt2
