from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, AsyncMock

import pytest

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import (
    NextAction,
    TelegramPayment,
    TelegramPaymentItem,
)
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.core.enums import UserAction
from app.core.services.exercise import ExerciseService
from app.core.services.payment import PaymentService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text


@pytest.fixture
def mock_user_service(mocker):
    service = AsyncMock(spec=UserService)
    return service


@pytest.fixture
def mock_exercise_service(mocker):
    service = AsyncMock(spec=ExerciseService)
    return service


@pytest.fixture
def mock_user_bot_profile_service(mocker):
    service = AsyncMock(spec=UserBotProfileService)
    return service


@pytest.fixture
def mock_payment_service(mocker):
    service = AsyncMock(spec=PaymentService)

    def _get_mock_payment_details(user_language: str):
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
                    amount=settings.min_session_unlock_payment,
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

    service.get_payment_unlock_details.side_effect = _get_mock_payment_details
    return service


pytestmark = pytest.mark.asyncio


async def test_get_next_action_returns_limit_reached_when_session_frozen(
    user_progress_service: UserProgressService,
    user: User,
    user_bot_profile: UserBotProfile,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=user)

    user_bot_profile.session_frozen_until = datetime.now(
        timezone.utc
    ) + timedelta(hours=1)
    if not user_bot_profile.user_language:
        user_bot_profile.user_language = user.telegram_data.get(
            'language_code', 'en'
        )

    user_progress_service.user_bot_profile_service.get_or_create = AsyncMock(
        return_value=(user_bot_profile, False)
    )
    user_progress_service.user_bot_profile_service.update_session = AsyncMock(
        return_value=user_bot_profile
    )

    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=user_bot_profile.bot_id
    )

    user_progress_service.user_service.get_by_id.assert_awaited_once_with(
        user.user_id
    )
    assert result.action == UserAction.limit_reached
    assert result.payment_info is not None
    assert isinstance(result.payment_info, TelegramPayment)
    assert len(result.payment_info.prices) > 0

    assert result.message == get_text(
        Messages.LIMIT_REACHED,
        language_code=user_bot_profile.user_language,
        pause_time=str(
            user_bot_profile.session_frozen_until - datetime.now(timezone.utc)
        ).split('.')[0],
    )


async def test_get_next_action_returns_new_exercise(
    user_progress_service: UserProgressService,
    user: User,
    user_bot_profile: UserBotProfile,
    fill_in_the_blank_exercise: Exercise,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=user)

    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 0
    user_bot_profile.exercises_get_in_set = 0
    user_bot_profile.errors_count_in_set = 0
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    if not user_bot_profile.user_language:
        user_bot_profile.user_language = user.telegram_data.get(
            'language_code', 'en'
        )

    user_progress_service.user_bot_profile_service.get_or_create = AsyncMock(
        return_value=(user_bot_profile, False)
    )

    async def mock_update_session_effect(**kwargs):
        for key, value in kwargs.items():
            if hasattr(user_bot_profile, key):
                setattr(user_bot_profile, key, value)
        return user_bot_profile

    user_progress_service.user_bot_profile_service.update_session = AsyncMock(
        side_effect=mock_update_session_effect
    )
    user_progress_service.exercise_service.get_next_exercise = AsyncMock(
        return_value=fill_in_the_blank_exercise
    )

    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=user_bot_profile.bot_id
    )

    user_progress_service.user_service.get_by_id.assert_awaited_once_with(
        user.user_id
    )
    user_progress_service.exercise_service.get_next_exercise.assert_awaited_once_with(
        exercise_type=fill_in_the_blank_exercise.exercise_type,
        topic=fill_in_the_blank_exercise.topic,
        language_level=fill_in_the_blank_exercise.language_level,
        user_id=user.user_id,
        target_language=user_bot_profile.bot_id.value,
        user_language=user_bot_profile.user_language,
    )
    user_progress_service.user_bot_profile_service.update_session.assert_awaited_once_with(
        user_id=user.user_id,
        bot_id=user_bot_profile.bot_id,
        exercises_get_in_session=1,
        exercises_get_in_set=1,
        last_exercise_at=ANY,
        last_long_break_reminder_sent_at=None,
        last_long_break_reminder_type_sent=None,
        current_streak_days=1,
    )
    assert result.action == UserAction.new_exercise
    assert result.exercise is not None
    assert user_bot_profile.exercises_get_in_session == 1
    assert user_bot_profile.exercises_get_in_set == 1


async def test_get_next_action_returns_praise_and_next_set_when_set_completed(
    user_progress_service: UserProgressService,
    user: User,
    user_bot_profile: UserBotProfile,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=user)

    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 3
    user_bot_profile.exercises_get_in_set = settings.exercises_in_set
    user_bot_profile.errors_count_in_set = 1
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    if not user_bot_profile.user_language:
        user_bot_profile.user_language = user.telegram_data.get(
            'language_code', 'en'
        )

    user_progress_service.user_bot_profile_service.get_or_create = AsyncMock(
        return_value=(user_bot_profile, False)
    )

    async def mock_update_session_effect(**kwargs):
        for key, value in kwargs.items():
            if hasattr(user_bot_profile, key):
                setattr(user_bot_profile, key, value)
        return user_bot_profile

    user_progress_service.user_bot_profile_service.update_session = AsyncMock(
        side_effect=mock_update_session_effect
    )

    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=user_bot_profile.bot_id
    )

    user_progress_service.user_service.get_by_id.assert_awaited_once_with(
        user.user_id
    )
    user_progress_service.user_bot_profile_service.update_session.assert_awaited_once_with(
        user_id=user.user_id,
        bot_id=user_bot_profile.bot_id,
        exercises_get_in_set=0,
        errors_count_in_set=0,
    )
    assert result.action == UserAction.praise_and_next_set
    assert user_bot_profile.exercises_get_in_session == 3
    assert user_bot_profile.exercises_get_in_set == 0


async def test_get_next_action_returns_congratulations_and_wait(
    user_progress_service: UserProgressService,
    user: User,
    user_bot_profile: UserBotProfile,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=user)

    user_bot_profile.session_frozen_until = None
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    user_bot_profile.exercises_get_in_session = (
        settings.sets_in_session * settings.exercises_in_set
    )
    user_bot_profile.exercises_get_in_set = 0
    if not user_bot_profile.user_language:
        user_bot_profile.user_language = user.telegram_data.get(
            'language_code', 'en'
        )

    user_progress_service.user_bot_profile_service.get_or_create = AsyncMock(
        return_value=(user_bot_profile, False)
    )

    async def mock_update_session_effect(**kwargs):
        for key, value in kwargs.items():
            if hasattr(user_bot_profile, key):
                setattr(user_bot_profile, key, value)
        return user_bot_profile

    user_progress_service.user_bot_profile_service.update_session = AsyncMock(
        side_effect=mock_update_session_effect
    )

    result: NextAction = await user_progress_service.get_next_action(
        user.user_id, bot_id=user_bot_profile.bot_id
    )

    user_progress_service.user_service.get_by_id.assert_awaited_once_with(
        user.user_id
    )
    user_progress_service.user_bot_profile_service.update_session.assert_awaited_once_with(
        user_id=user.user_id,
        bot_id=user_bot_profile.bot_id,
        session_frozen_until=ANY,
        wants_session_reminders=None,
    )
    assert result.action == UserAction.congratulations_and_wait
    assert result.payment_info is not None
    assert result.message == get_text(
        Messages.CONGRATULATIONS_AND_WAIT,
        language_code=user_bot_profile.user_language,
        exercise_num=user_bot_profile.exercises_get_in_session,
        pause_time=str(settings.delta_between_sessions).split('.')[0],
    )
    assert result.pause == settings.delta_between_sessions
    assert (
        user_bot_profile.exercises_get_in_session
        == settings.sets_in_session * settings.exercises_in_set
    )


async def test_get_next_action_raises_value_error_when_user_not_found(
    user_progress_service: UserProgressService,
    user: User,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(
        ValueError, match='User with provided ID not found in the database'
    ):
        await user_progress_service.get_next_action(
            user.user_id, bot_id=BotID.BG
        )


async def test_get_next_action_returns_error_when_no_exercise(
    user_progress_service: UserProgressService,
    user: User,
    user_bot_profile: UserBotProfile,
):
    user_progress_service.user_service.get_by_id = AsyncMock(return_value=user)

    user_bot_profile.session_frozen_until = None
    user_bot_profile.exercises_get_in_session = 0
    user_bot_profile.exercises_get_in_set = 0
    user_bot_profile.session_started_at = datetime.now(timezone.utc)
    if not user_bot_profile.user_language:
        user_bot_profile.user_language = user.telegram_data.get(
            'language_code', 'en'
        )

    user_progress_service.user_bot_profile_service.get_or_create = AsyncMock(
        return_value=(user_bot_profile, False)
    )
    user_progress_service.exercise_service.get_next_exercise = AsyncMock(
        return_value=None
    )

    result = await user_progress_service.get_next_action(
        user.user_id, bot_id=user_bot_profile.bot_id
    )

    assert result.action == UserAction.error
    assert result.message == get_text(
        Messages.ERROR_GETTING_NEW_EXERCISE, user_bot_profile.user_language
    )
