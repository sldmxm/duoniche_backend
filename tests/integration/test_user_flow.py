from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.config import settings
from app.core.entities.next_action_result import TelegramPayment
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID
from app.core.enums import LanguageLevel, UserAction
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text
from app.db.repositories.user import SQLAlchemyUserRepository
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)

# Используем pytestmark для применения ко всем тестам в модуле
pytestmark = pytest.mark.asyncio


async def test_flow_session_limit_reached_offers_payment(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
):
    # Arrange: Create user and profile in a separate, committed transaction
    now = datetime.now(timezone.utc)
    user_id = user_data['user_id']
    bot_id = BotID.BG
    user_language = 'ru'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        user_bot_profile, _ = await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )

        await setup_profile_service.update_session(
            user_id=db_user.user_id,
            bot_id=bot_id,
            exercises_get_in_session=(
                settings.exercises_in_set * settings.sets_in_session
            ),
            session_started_at=now - timedelta(minutes=1),
            session_frozen_until=None,
        )
        await setup_session.commit()

    # Act
    with freeze_time(now):
        next_action = await user_progress_service.get_next_action(
            user_id=db_user.user_id, bot_id=BotID.BG
        )

    # Assert
    assert next_action.action == UserAction.congratulations_and_wait
    assert next_action.payment_info is not None
    assert isinstance(next_action.payment_info, TelegramPayment)
    assert next_action.payment_info.currency == 'XTR'
    assert next_action.payment_info.button_text == get_text(
        PaymentMessages.BUTTON_TEXT, user_language
    )
    assert next_action.payment_info.prices[0].label == get_text(
        PaymentMessages.ITEM_LABEL_TIER_1, user_language
    )
    assert next_action.payment_info.prices[0].amount == 20

    expected_message_key = Messages.CONGRATULATIONS_AND_WAIT
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        exercise_num=settings.exercises_in_set * settings.sets_in_session,
        pause_time=str(settings.delta_between_sessions).split('.')[0],
    )
    assert next_action.message == expected_message
    assert next_action.pause == settings.delta_between_sessions


async def test_flow_frozen_user_offers_payment(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
):
    # Arrange
    now = datetime.now(timezone.utc)
    frozen_until = now + timedelta(hours=1)
    user_id = user_data['user_id']
    bot_id = BotID.BG
    user_language = 'en'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        user_bot_profile, _ = await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )

        await setup_session.flush()

        await setup_profile_service.update_session(
            user_id=db_user.user_id,
            bot_id=bot_id,
            session_frozen_until=frozen_until,
        )
        await setup_session.commit()

    expected_payment_amount = 20
    expected_item_label_key = PaymentMessages.ITEM_LABEL_TIER_1

    # Act
    with freeze_time(now):
        next_action = await user_progress_service.get_next_action(
            user_id=db_user.user_id, bot_id=BotID.BG
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
        expected_item_label_key, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_payment_amount

    expected_message_key = Messages.LIMIT_REACHED
    delta_to_next_session = str(frozen_until - now).split('.')[0]
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        pause_time=delta_to_next_session,
    )
    assert next_action.message == expected_message


async def test_flow_new_exercise_for_active_user(
    user_progress_service: UserProgressService,
    async_session_maker: async_sessionmaker,
    user_data,
    fill_sample_exercises,
    user_bot_profile_service,
):
    # Arrange
    user_id = user_data['user_id']
    bot_id = BotID.BG
    user_language = 'bg'

    async with async_session_maker() as setup_session:
        user_repo = SQLAlchemyUserRepository(setup_session)
        profile_repo = SQLAlchemyUserBotProfileRepository(setup_session)
        setup_user_service = UserService(user_repo)
        setup_profile_service = UserBotProfileService(profile_repo)

        user_entity = User(
            user_id=user_id,
            telegram_id=user_data['telegram_id'],
            username=user_data['username'],
            name=user_data['name'],
            telegram_data={'language_code': user_language},
        )
        db_user, _ = await setup_user_service.get_or_create(user_entity)

        await setup_profile_service.get_or_create(
            user_id=db_user.user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=LanguageLevel.A1,
        )
        await setup_profile_service.reset_and_start_new_session(
            user_id=db_user.user_id, bot_id=bot_id
        )
        await setup_session.commit()

    # Act
    next_action = await user_progress_service.get_next_action(
        user_id=user_id, bot_id=bot_id
    )

    # Assert
    assert next_action.action == UserAction.new_exercise
    assert next_action.exercise is not None
    assert (
        next_action.message is None
    )  # Сообщение не ожидается при новом упражнении
    assert next_action.payment_info is None  # Оплата не ожидается

    # Проверяем, что счетчики в БД обновились
    updated_profile = await user_bot_profile_service.get(
        db_user.user_id, BotID.BG
    )
    assert updated_profile is not None
    assert updated_profile.exercises_get_in_session == 1
    assert updated_profile.exercises_get_in_set == 1
    assert updated_profile.last_exercise_at is not None
