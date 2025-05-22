from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from freezegun import freeze_time

from app.config import settings
from app.core.entities.next_action_result import TelegramPayment
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.enums import LanguageLevel, UserAction
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text


@pytest.fixture
def mock_user_service():
    return AsyncMock()


@pytest.fixture
def mock_exercise_service():
    return AsyncMock()


@pytest.fixture
def mock_user_bot_profile_service():
    return AsyncMock()


@pytest.fixture
def user_progress_service(
    mock_user_service, mock_exercise_service, mock_user_bot_profile_service
):
    return UserProgressService(
        user_service=mock_user_service,
        exercise_service=mock_exercise_service,
        user_bot_profile_service=mock_user_bot_profile_service,
    )


@pytest.fixture
def sample_user():
    return User(
        user_id=1,
        telegram_id='12345',
        username='testuser',
        name='Test User',
        telegram_data={'language_code': 'en'},
        cohort='2023-01-01',
        plan='free',
    )


@pytest.fixture
def sample_user_bot_profile():
    return UserBotProfile(
        user_id=1,
        bot_id=BotID.BG,
        user_language='en',
        language_level=LanguageLevel.A1,
        exercises_get_in_session=0,
        exercises_get_in_set=0,
        errors_count_in_set=0,
        session_started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        last_exercise_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        session_frozen_until=None,
        wants_session_reminders=None,
        last_long_break_reminder_type_sent=None,
        last_long_break_reminder_sent_at=None,
    )


@freeze_time('2023-01-15 12:00:00 UTC')
@pytest.mark.asyncio
@patch('app.core.services.user_progress.random.randint')
async def test_get_next_action_when_frozen_offers_payment(
    mock_randint,
    user_progress_service: UserProgressService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
    mock_user_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
):
    # Arrange
    now = datetime.now(timezone.utc)
    sample_user_bot_profile.session_frozen_until = now + timedelta(hours=1)
    user_language = sample_user_bot_profile.user_language
    expected_mocked_amount = 5
    mock_randint.return_value = expected_mocked_amount

    mock_user_service.get_by_id.return_value = sample_user
    mock_user_bot_profile_service.get_or_create.return_value = (
        sample_user_bot_profile,
        False,
    )

    # Act
    next_action = await user_progress_service.get_next_action(
        user_id=sample_user.user_id, bot_id=sample_user_bot_profile.bot_id
    )

    # Assert
    assert next_action.action == UserAction.limit_reached
    assert next_action.payment_info is not None
    assert isinstance(next_action.payment_info, TelegramPayment)
    assert next_action.payment_info.currency == 'XTR'
    assert next_action.payment_info.button_text == get_text(
        PaymentMessages.BUTTON_TEXT, user_language
    )
    assert next_action.payment_info.title == get_text(
        PaymentMessages.TITLE, user_language
    )
    assert next_action.payment_info.prices[0].label == get_text(
        PaymentMessages.ITEM_LABEL, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_mocked_amount
    mock_randint.assert_called_once_with(
        settings.min_session_unlock_payment,
        settings.max_session_unlock_payment,
    )

    expected_message_key = Messages.LIMIT_REACHED
    delta_to_next_session = str(
        sample_user_bot_profile.session_frozen_until - now
    ).split('.')[0]
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        pause_time=delta_to_next_session,
    )
    assert next_action.message == expected_message


@pytest.mark.asyncio
@patch('app.core.services.user_progress.random.randint')
async def test_get_next_action_when_session_limit_reached_offers_payment(
    mock_randint,
    user_progress_service: UserProgressService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
    mock_user_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
):
    # Arrange
    # Имитируем, что пользователь достиг лимита упражнений в сессии
    sample_user_bot_profile.exercises_get_in_session = (
        settings.exercises_in_set * settings.sets_in_session
    )
    sample_user_bot_profile.session_frozen_until = (
        None  # Сессия еще не заморожена
    )
    user_language = sample_user_bot_profile.user_language
    expected_mocked_amount = 10
    mock_randint.return_value = expected_mocked_amount

    mock_user_service.get_by_id.return_value = sample_user
    mock_user_bot_profile_service.get_or_create.return_value = (
        sample_user_bot_profile,
        False,
    )
    # Мокаем update_session, который вызывается для заморозки сессии
    mock_user_bot_profile_service.update_session.return_value = (
        sample_user_bot_profile
    )

    # Act
    next_action = await user_progress_service.get_next_action(
        user_id=sample_user.user_id, bot_id=sample_user_bot_profile.bot_id
    )

    # Assert
    assert next_action.action == UserAction.congratulations_and_wait
    assert next_action.payment_info is not None
    assert isinstance(next_action.payment_info, TelegramPayment)
    assert next_action.payment_info.currency == 'XTR'
    assert next_action.payment_info.button_text == get_text(
        PaymentMessages.BUTTON_TEXT, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_mocked_amount
    mock_randint.assert_called_once_with(
        settings.min_session_unlock_payment,
        settings.max_session_unlock_payment,
    )

    expected_message_key = Messages.CONGRATULATIONS_AND_WAIT
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        exercise_num=sample_user_bot_profile.exercises_get_in_session,
        pause_time=str(settings.delta_between_sessions).split('.')[0],
    )
    assert next_action.message == expected_message
    assert next_action.pause == settings.delta_between_sessions

    # Проверяем, что сессия была заморожена
    mock_user_bot_profile_service.update_session.assert_called_once()
    call_args = mock_user_bot_profile_service.update_session.call_args[1]
    assert call_args['user_id'] == sample_user.user_id
    assert call_args['bot_id'] == sample_user_bot_profile.bot_id
    assert 'session_frozen_until' in call_args
    assert call_args['wants_session_reminders'] is None
