from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.core.consts import (
    DELTA_BETWEEN_SESSIONS,
    EXERCISES_IN_SESSION,
    EXERCISES_IN_SET,
)
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.enums import UserAction
from app.core.repositories.user import UserRepository
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_progress import UserProgressService


# --- Mocks for Dependencies ---
@pytest.fixture
def mock_user_repo(mocker):
    return mocker.AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_user_service(mocker):
    return mocker.AsyncMock(spec=UserService)


@pytest.fixture
def mock_exercise_service(mocker):
    return mocker.AsyncMock(spec=ExerciseService)


# --- Service Instance Fixture ---
@pytest.fixture
def user_progress_service(
    mock_user_service,
    mock_exercise_service,
) -> UserProgressService:
    """Provides a UserProgressService instance with mocked dependencies."""
    return UserProgressService(
        user_service=mock_user_service,
        exercise_service=mock_exercise_service,
    )


pytestmark = pytest.mark.asyncio


class TestUserProgressService:
    async def test_get_next_action_limit_reached(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        user: User,
    ):
        """
        Scenario: The user is waiting for the next session,
            and the waiting period has not elapsed.
        Expected: Return NextAction with UserAction.limit_reached and a pause.
        """
        # Arrange
        user.is_waiting_next_session = True
        user.last_exercise_at = datetime.now(timezone.utc) - timedelta(
            minutes=10
        )  # Set last_exercise_at to 10 minutes ago
        mock_user_service.get_by_id.return_value = user

        # Act
        result: NextAction = await user_progress_service.get_next_action(
            user.user_id
        )

        # Assert
        mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
        assert result.action == UserAction.limit_reached

    async def test_get_next_action_new_exercise(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        mock_exercise_service: AsyncMock,
        user: User,
        fill_in_the_blank_exercise: Exercise,
    ):
        """
        Scenario: The user is not waiting, has not completed a session,
            and has not completed a set.
        Expected: Return NextAction with UserAction.new_exercise
            and an exercise.
        """
        # Arrange
        user.is_waiting_next_session = False
        user.exercises_get_in_session = 0
        user.exercises_get_in_set = 0
        mock_user_service.get_by_id.return_value = user
        mock_exercise_service.get_or_create_next_exercise.return_value = (
            fill_in_the_blank_exercise
        )
        mock_user_service.update.return_value = None

        # Act
        result: NextAction = await user_progress_service.get_next_action(
            user.user_id
        )

        # Assert
        mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
        mock_es = mock_exercise_service
        mock_es.get_or_create_next_exercise.assert_awaited_once_with(user)
        mock_user_service.update.assert_awaited_once_with(user)
        assert result.action == UserAction.new_exercise
        assert result.exercise is not None
        assert user.exercises_get_in_session == 1
        assert user.exercises_get_in_set == 1

    async def test_get_next_action_praise_and_next_set(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        user: User,
    ):
        """
        Scenario: The user has completed a set of exercises.
        Expected: Return NextAction with UserAction.praise_and_next_set
            and a praise message.
        """
        # Arrange
        user.is_waiting_next_session = False
        user.exercises_get_in_session = 3
        user.exercises_get_in_set = EXERCISES_IN_SET
        user.errors_count_in_set = 1
        mock_user_service.get_by_id.return_value = user
        mock_user_service.update.return_value = None

        # Act
        result: NextAction = await user_progress_service.get_next_action(
            user.user_id
        )

        # Assert
        mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
        mock_user_service.update.assert_awaited_once_with(user)
        assert result.action == UserAction.praise_and_next_set
        assert result.message is not None
        assert user.exercises_get_in_set == 0
        assert user.errors_count_in_set == 0
        assert user.exercises_get_in_session == 3

    async def test_get_next_action_congratulations_and_wait(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        user: User,
    ):
        """
        Scenario: The user has completed a session of exercises.
        Expected: Return NextAction with UserAction.congratulations_and_wait,
            a congratulatory message, and a pause.
        """
        # Arrange
        user.is_waiting_next_session = False
        user.exercises_get_in_session = EXERCISES_IN_SESSION
        user.exercises_get_in_set = 0
        mock_user_service.get_by_id.return_value = user
        mock_user_service.update.return_value = None

        # Act
        result: NextAction = await user_progress_service.get_next_action(
            user.user_id
        )

        # Assert
        mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
        mock_user_service.update.assert_awaited_once_with(user)
        assert result.action == UserAction.congratulations_and_wait
        assert result.message is not None
        assert result.pause == DELTA_BETWEEN_SESSIONS
        assert user.exercises_get_in_session == 0
        assert user.exercises_get_in_set == 0

    async def test_get_next_action_user_not_found(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        user: User,
    ):
        """
        Scenario: The user is not found in the database.
        Expected: Raise ValueError.
        """
        # Arrange
        mock_user_service.get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValueError):
            await user_progress_service.get_next_action(user.user_id)

    async def test_get_next_action_no_exercise(
        self,
        user_progress_service: UserProgressService,
        mock_user_service: AsyncMock,
        mock_exercise_service: AsyncMock,
        user: User,
    ):
        """
        Scenario: There is no suitable exercise for the user.
        Expected: Error message.
        """
        # Arrange
        user.is_waiting_next_session = False
        user.exercises_get_in_session = 0
        user.exercises_get_in_set = 0
        mock_user_service.get_by_id.return_value = user
        mock_exercise_service.get_or_create_next_exercise.return_value = None

        result: NextAction = await user_progress_service.get_next_action(
            user.user_id
        )

        # Act & Assert
        assert result.action == UserAction.error
