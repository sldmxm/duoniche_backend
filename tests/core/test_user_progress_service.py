from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock

import pytest

from app.core.consts import (
    DELTA_BETWEEN_SESSIONS,
    EXERCISES_IN_SESSION,
    EXERCISES_IN_SET,
    RENEWING_SET_PERIOD,
    SETS_IN_SESSION,
)
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.enums import UserAction
from app.core.repositories.user import UserRepository
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.texts import MESSAGES_TRANSLATIONS, Messages, get_text


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


@pytest.fixture
def mock_user_bot_profile_service(mocker):
    return mocker.AsyncMock(spec=UserBotProfileService)


# --- Service Instance Fixture ---
@pytest.fixture
def user_progress_service(
    mock_user_service,
    mock_exercise_service,
    mock_user_bot_profile_service,
) -> UserProgressService:
    """Provides a UserProgressService instance with mocked dependencies."""
    return UserProgressService(
        user_service=mock_user_service,
        exercise_service=mock_exercise_service,
        user_bot_profile_service=mock_user_bot_profile_service,
    )


pytestmark = pytest.mark.asyncio


async def test_get_next_action_returns_limit_reached_when_session_frozen(
    user_progress_service: UserProgressService,
    mock_user_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    user: User,
    user_bot_profile: UserBotProfile,
):
    """
    Scenario: The user is waiting for the next session,
        and the waiting period has not elapsed.
    Expected: Return NextAction with UserAction.limit_reached and a pause.
    """
    # Arrange
    mock_user_service.get_by_id.return_value = user
    user_bot_profile.session_frozen_until = datetime.now(
        timezone.utc
    ) + timedelta(hours=1)
    mock_user_bot_profile_service.get_or_create.return_value = (
        user_bot_profile,
        True,
    )
    mock_user_bot_profile_service.update_session.return_value = (
        user_bot_profile
    )

    # Act
    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=BotID.BG
    )

    # Assert
    mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
    assert result.action == UserAction.limit_reached
    assert result.message == get_text(
        Messages.LIMIT_REACHED,
        language_code=user.user_language,
        pause_time=str(timedelta(seconds=59 * 60 + 59)).split('.')[0],
    )


async def test_get_next_action_returns_new_exercise(
    user_progress_service: UserProgressService,
    mock_user_service: AsyncMock,
    mock_exercise_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    user_bot_profile: UserBotProfile,
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
    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 0
    user_bot_profile.exercises_get_in_set = 0
    user_bot_profile.errors_count_in_set = 0
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    mock_user_service.get_by_id.return_value = user
    mock_user_bot_profile_service.get_or_create.return_value = (
        user_bot_profile,
        True,
    )
    mock_user_bot_profile_service.update_session.return_value = (
        user_bot_profile
    )
    mock_exercise_service.get_next_exercise.return_value = (
        fill_in_the_blank_exercise
    )

    # Act
    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=BotID.BG
    )

    print(result)

    # Assert
    mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)

    mock_exercise_service.get_next_exercise.assert_awaited_once_with(
        exercise_type=fill_in_the_blank_exercise.exercise_type,
        topic=fill_in_the_blank_exercise.topic,
        language_level=fill_in_the_blank_exercise.language_level,
        user_id=user.user_id,
        target_language=user_bot_profile.bot_id.value,
        user_language=user_bot_profile.user_language,
    )
    mock_user_bot_profile_service.update_session.assert_awaited_once_with(
        exercises_get_in_session=1,
        exercises_get_in_set=1,
        last_exercise_at=ANY,
        user_id=12345,
        bot_id=BotID.BG,
        last_long_break_reminder_sent_at=None,
        last_long_break_reminder_type_sent=None,
    )
    assert result.action == UserAction.new_exercise
    assert result.exercise is not None
    assert user_bot_profile.exercises_get_in_session == 1
    assert user_bot_profile.exercises_get_in_set == 1


async def test_get_next_action_returns_praise_and_next_set_when_set_completed(
    user_progress_service: UserProgressService,
    mock_user_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    user: User,
    user_bot_profile,
):
    """
    Scenario: The user has completed a set of exercises.
    Expected: Return NextAction with UserAction.praise_and_next_set
        and a praise message.
    """
    # Arrange
    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 3
    user_bot_profile.exercises_get_in_set = EXERCISES_IN_SET
    user_bot_profile.errors_count_in_set = 1
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    mock_user_service.get_by_id.return_value = user
    mock_user_bot_profile_service.get_or_create.return_value = (
        user_bot_profile,
        True,
    )
    mock_user_bot_profile_service.update_session.return_value = (
        user_bot_profile
    )

    # Act
    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=BotID.BG
    )

    # Assert
    mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
    mock_user_bot_profile_service.update_session.assert_awaited_once_with(
        user_id=user.user_id,
        bot_id=BotID.BG,
        exercises_get_in_set=0,
        errors_count_in_set=0,
    )
    assert result.action == UserAction.praise_and_next_set
    assert (
        result.message
        in MESSAGES_TRANSLATIONS[Messages.PRAISE_AND_NEXT_SET][
            user.user_language
        ]
    )
    assert user_bot_profile.exercises_get_in_session == 3


async def test_get_next_action_returns_congratulations_and_wait(
    user_progress_service: UserProgressService,
    mock_user_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    user: User,
    user_bot_profile: UserBotProfile,
):
    """
    Scenario: The user has completed a session of exercises.
    Expected: Return NextAction with UserAction.congratulations_and_wait,
        a congratulatory message, and a pause.
    """
    # Arrange
    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = EXERCISES_IN_SESSION
    user_bot_profile.exercises_get_in_set = 0
    user_bot_profile.session_started_at = datetime.now(
        timezone.utc
    ) - RENEWING_SET_PERIOD * (SETS_IN_SESSION - 1)
    mock_user_service.get_by_id.return_value = user
    mock_user_bot_profile_service.get_or_create.return_value = (
        user_bot_profile,
        True,
    )
    mock_user_bot_profile_service.update_session.return_value = (
        user_bot_profile
    )

    # Act
    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=BotID.BG
    )

    # Assert
    mock_user_service.get_by_id.assert_awaited_once_with(user.user_id)
    mock_user_bot_profile_service.update_session.assert_awaited_once_with(
        user_id=user.user_id,
        bot_id=BotID.BG,
        session_frozen_until=ANY,
    )
    assert result.action == UserAction.congratulations_and_wait
    assert result.message == get_text(
        Messages.CONGRATULATIONS_AND_WAIT,
        language_code=user_bot_profile.user_language,
        exercise_num=EXERCISES_IN_SESSION,
        pause_time=str(DELTA_BETWEEN_SESSIONS).split('.')[0],
    )
    assert result.pause == DELTA_BETWEEN_SESSIONS
    assert user_bot_profile.exercises_get_in_session == EXERCISES_IN_SESSION
    assert user_bot_profile.exercises_get_in_set == 0


async def test_get_next_action_raises_value_error_when_user_not_found(
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
        await user_progress_service.get_next_action(
            user.user_id, bot_id=BotID.BG
        )


async def test_get_next_action_returns_error_when_no_exercise(
    user_progress_service: UserProgressService,
    mock_user_service: AsyncMock,
    mock_exercise_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    user: User,
    user_bot_profile: UserBotProfile,
):
    """
    Scenario: There is no suitable exercise for the user.
    Expected: Error message.
    """
    # Arrange
    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 0
    user_bot_profile.exercises_get_in_set = 0
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    mock_user_service.get_by_id.return_value = user
    mock_user_bot_profile_service.get_or_create.return_value = (
        user_bot_profile,
        True,
    )
    mock_exercise_service.get_next_exercise.return_value = None

    # Act & Assert
    assert await user_progress_service.get_next_action(
        user.user_id, bot_id=BotID.BG
    ) == NextAction(
        action=UserAction.error,
        message=get_text(
            Messages.ERROR_GETTING_NEW_EXERCISE, user.user_language
        ),
    )
