from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from freezegun import freeze_time

from app.config import settings
from app.core.entities.next_action_result import (
    TelegramPayment,
    TelegramPaymentItem,
)
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.entities.user_settings import UserSettings
from app.core.enums import LanguageLevel, UserAction
from app.core.services.payment import PaymentService
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text


@pytest.fixture
def mock_user_service():
    service = AsyncMock()
    service.get_by_id.return_value = User(
        user_id=1,
        telegram_id='12345',
        username='testuser',
        name='Test User',
        telegram_data={'language_code': 'en'},
        cohort='2023-01-01',
        plan='free',
    )
    return service


@pytest.fixture
def mock_exercise_service():
    return AsyncMock()


@pytest.fixture
def mock_user_setting_service():
    service = AsyncMock()
    service.get_effective_settings.return_value = UserSettings(
        session_exercise_limit=(
            settings.exercises_in_set * settings.sets_in_session
        ),
        min_session_interval_minutes=int(
            settings.delta_between_sessions.total_seconds() / 60
        ),
        exercises_in_set=settings.exercises_in_set,
    )
    return service


@pytest.fixture
def mock_user_bot_profile_service():
    service = AsyncMock()
    service.get_or_create.return_value = (
        UserBotProfile(
            user_id=1,
            bot_id=BotID.BG,
            user_language='en',
            language_level=LanguageLevel.A1,
            exercises_get_in_session=0,
            exercises_get_in_set=0,
            errors_count_in_set=0,
            session_started_at=datetime.now(timezone.utc)
            - timedelta(minutes=10),
            last_exercise_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            session_frozen_until=None,
            wants_session_reminders=None,
            last_long_break_reminder_type_sent=None,
            last_long_break_reminder_sent_at=None,
        ),
        False,
    )
    service.reset_and_start_new_session = AsyncMock(
        return_value=service.get_or_create.return_value[0]
    )
    service.update_session = AsyncMock(
        return_value=service.get_or_create.return_value[0]
    )
    return service


@pytest.fixture
def mock_payment_service():
    service = AsyncMock(spec=PaymentService)

    def _get_mock_payment_details(
        user_id: int, bot_id: BotID, user_language: str
    ):
        payment_tiers_config = [
            (20, PaymentMessages.ITEM_LABEL_TIER_1),
            (50, PaymentMessages.ITEM_LABEL_TIER_2),
            (100, PaymentMessages.ITEM_LABEL_TIER_3),
            (200, PaymentMessages.ITEM_LABEL_TIER_4),
            (500, PaymentMessages.ITEM_LABEL_TIER_5),
            (1000, PaymentMessages.ITEM_LABEL_TIER_6),
        ]
        prices = []
        for amount, label_key in payment_tiers_config:
            prices.append(
                TelegramPaymentItem(
                    label=get_text(label_key, user_language),
                    amount=amount,
                )
            )
        if not prices:
            prices.append(
                TelegramPaymentItem(
                    label=get_text(PaymentMessages.ITEM_LABEL, user_language),
                    amount=5,
                )
            )

        return TelegramPayment(
            button_text=get_text(PaymentMessages.BUTTON_TEXT, user_language),
            title=get_text(PaymentMessages.TITLE, user_language),
            description=get_text(PaymentMessages.DESCRIPTION, user_language),
            currency='XTR',
            prices=prices,
            thanks_answer=get_text(
                PaymentMessages.THANKS_ANSWER, user_language
            ),
        )

    service.get_unlock_payment_details.side_effect = _get_mock_payment_details
    return service


@pytest.fixture
def sample_user(mock_user_service: AsyncMock):
    return mock_user_service.get_by_id.return_value


@pytest.fixture
def sample_user_bot_profile(mock_user_bot_profile_service: AsyncMock):
    return mock_user_bot_profile_service.get_or_create.return_value[0]


@pytest.fixture
def user_progress_service(
    mock_user_service: AsyncMock,
    mock_exercise_service: AsyncMock,
    mock_user_bot_profile_service: AsyncMock,
    mock_payment_service: AsyncMock,
    mock_user_setting_service: AsyncMock,
):
    return UserProgressService(
        user_service=mock_user_service,
        exercise_service=mock_exercise_service,
        user_bot_profile_service=mock_user_bot_profile_service,
        payment_service=mock_payment_service,
        user_settings_service=mock_user_setting_service,
    )


@freeze_time('2023-01-15 12:00:00 UTC')
@pytest.mark.asyncio
async def test_get_next_action_when_frozen_offers_payment(
    user_progress_service: UserProgressService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    now = datetime.now(timezone.utc)
    sample_user_bot_profile.session_frozen_until = now + timedelta(hours=1)
    user_language = sample_user_bot_profile.user_language
    expected_payment_amount = 20
    expected_item_label_key = PaymentMessages.ITEM_LABEL_TIER_1

    user_progress_service.user_service.get_by_id.return_value = sample_user
    (
        user_progress_service.user_bot_profile_service.get_or_create
    ).return_value = (
        sample_user_bot_profile,
        False,
    )

    next_action = await user_progress_service.get_next_action(
        user_id=sample_user.user_id, bot_id=sample_user_bot_profile.bot_id
    )

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
        expected_item_label_key, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_payment_amount

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
async def test_get_next_action_when_session_limit_reached_offers_payment(
    user_progress_service: UserProgressService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Configure UserSettingsService mock for this specific test
    test_session_limit = settings.exercises_in_set * settings.sets_in_session
    test_min_interval_minutes = int(
        settings.delta_between_sessions.total_seconds() / 60
    )
    (
        user_progress_service.user_settings_service.get_effective_settings
    ).return_value = UserSettings(
        session_exercise_limit=test_session_limit,
        min_session_interval_minutes=test_min_interval_minutes,
        exercises_in_set=settings.exercises_in_set,
    )

    sample_user_bot_profile.exercises_get_in_session = test_session_limit
    sample_user_bot_profile.session_frozen_until = None
    user_language = sample_user_bot_profile.user_language
    expected_payment_amount = 20
    expected_item_label_key = PaymentMessages.ITEM_LABEL_TIER_1

    user_progress_service.user_service.get_by_id.return_value = sample_user

    (
        user_progress_service.user_bot_profile_service.get_or_create
    ).return_value = (
        sample_user_bot_profile,
        False,
    )
    (
        user_progress_service.user_bot_profile_service.update_session
    ).return_value = sample_user_bot_profile

    next_action = await user_progress_service.get_next_action(
        user_id=sample_user.user_id, bot_id=sample_user_bot_profile.bot_id
    )

    assert next_action.action == UserAction.congratulations_and_wait
    assert next_action.payment_info is not None
    assert isinstance(next_action.payment_info, TelegramPayment)
    assert next_action.payment_info.currency == 'XTR'
    assert next_action.payment_info.button_text == get_text(
        PaymentMessages.BUTTON_TEXT, user_language
    )
    assert next_action.payment_info.prices[0].label == get_text(
        expected_item_label_key, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_payment_amount

    expected_message_key = Messages.CONGRATULATIONS_AND_WAIT
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        exercise_num=sample_user_bot_profile.exercises_get_in_session,
        pause_time=str(timedelta(minutes=test_min_interval_minutes)).split(
            '.'
        )[0],
    )
    assert next_action.message == expected_message
    assert next_action.pause == timedelta(minutes=test_min_interval_minutes)

    prof_serv = user_progress_service
    prof_serv.user_bot_profile_service.update_session.assert_called_once()
    call_args = prof_serv.user_bot_profile_service.update_session.call_args[1]
    assert call_args['user_id'] == sample_user.user_id
    assert call_args['bot_id'] == sample_user_bot_profile.bot_id
    assert 'session_frozen_until' in call_args
    assert call_args['wants_session_reminders'] is None
