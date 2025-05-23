from datetime import datetime, timedelta, timezone

import pytest
from freezegun import freeze_time

from app.config import settings
from app.core.entities.next_action_result import TelegramPayment
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID
from app.core.enums import LanguageLevel, UserAction
from app.core.services.user_progress import UserProgressService
from app.core.texts import Messages, PaymentMessages, get_text

# Используем pytestmark для применения ко всем тестам в модуле
pytestmark = pytest.mark.asyncio


async def test_flow_session_limit_reached_offers_payment(
    user_progress_service: UserProgressService,  # Фикстура из conftest
    user_service,  # Фикстура из conftest
    user_bot_profile_service,  # Фикстура из conftest
    user_data,  # Фикстура из conftest
):
    # Arrange: Создаем пользователя и его профиль в БД
    user_entity = User(
        telegram_id=user_data['telegram_id'],
        username=user_data['username'],
        name=user_data['name'],
        telegram_data={'language_code': 'ru'},  # Явно задаем язык
    )
    db_user, _ = await user_service.get_or_create(user_entity)
    assert db_user.user_id is not None

    # Создаем профиль бота, имитируя достижение лимита сессии
    # Устанавливаем exercises_get_in_session равным лимиту
    # session_started_at должен быть таким, чтобы renewed_sets был 0
    # для предсказуемого current_exercises_limit
    now = datetime.now(timezone.utc)
    user_bot_profile, _ = await user_bot_profile_service.get_or_create(
        user_id=db_user.user_id,
        bot_id=BotID.BG,
        user_language='ru',
        language_level=LanguageLevel.A1,
    )
    # Обновляем профиль, чтобы он соответствовал состоянию "лимит достигнут"
    user_bot_profile = await user_bot_profile_service.update_session(
        user_id=db_user.user_id,
        bot_id=BotID.BG,
        exercises_get_in_session=(
            settings.exercises_in_set * settings.sets_in_session
        ),
        session_started_at=now
        - timedelta(minutes=1),  # Сессия только что началась
        session_frozen_until=None,  # Убедимся, что не заморожен
    )
    user_language = user_bot_profile.user_language
    expected_payment_amount = 20  # Первая сумма из payment_tiers
    expected_item_label_key = PaymentMessages.ITEM_LABEL_TIER_1

    # Act
    with freeze_time(now):  # Замораживаем время для консистентности
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
        expected_item_label_key, user_language
    )
    assert next_action.payment_info.prices[0].amount == expected_payment_amount

    expected_message_key = Messages.CONGRATULATIONS_AND_WAIT
    expected_message = get_text(
        expected_message_key,
        language_code=user_language,
        exercise_num=user_bot_profile.exercises_get_in_session,
        pause_time=str(settings.delta_between_sessions).split('.')[0],
    )
    assert next_action.message == expected_message
    assert next_action.pause == settings.delta_between_sessions

    # Проверяем, что сессия была заморожена в БД
    updated_profile = await user_bot_profile_service.get(
        db_user.user_id, BotID.BG
    )
    assert updated_profile is not None
    assert updated_profile.session_frozen_until is not None
    assert updated_profile.session_frozen_until > now


async def test_flow_frozen_user_offers_payment(
    user_progress_service: UserProgressService,
    user_service,
    user_bot_profile_service,
    user_data,
):
    # Arrange: Создаем пользователя и его профиль в БД
    user_entity = User(
        telegram_id=user_data['telegram_id'],
        username=user_data['username'],
        name=user_data['name'],
        telegram_data={'language_code': 'en'},
    )
    db_user, _ = await user_service.get_or_create(user_entity)
    assert db_user.user_id is not None

    now = datetime.now(timezone.utc)
    frozen_until = now + timedelta(hours=1)

    user_bot_profile, _ = await user_bot_profile_service.get_or_create(
        user_id=db_user.user_id,
        bot_id=BotID.BG,
        user_language='en',
        language_level=LanguageLevel.A1,
    )
    # Обновляем профиль, чтобы он был заморожен
    user_bot_profile = await user_bot_profile_service.update_session(
        user_id=db_user.user_id,
        bot_id=BotID.BG,
        session_frozen_until=frozen_until,
    )

    user_language = user_bot_profile.user_language
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
    user_service,
    user_bot_profile_service,
    exercise_service,  # Для добавления упражнений в БД
    user_data,
    fill_sample_exercises,
):
    # Arrange: Создаем пользователя и его профиль в БД
    user_entity = User(
        telegram_id=user_data['telegram_id'],
        username=user_data['username'],
        name=user_data['name'],
        telegram_data={'language_code': 'bg'},  # Болгарский язык
    )
    db_user, _ = await user_service.get_or_create(user_entity)
    assert db_user.user_id is not None

    # Создаем профиль бота, который готов к новому упражнению
    user_bot_profile, _ = await user_bot_profile_service.get_or_create(
        user_id=db_user.user_id,
        bot_id=BotID.BG,  # Болгарский бот
        user_language='bg',  # Язык пользователя
        language_level=LanguageLevel.A1,  # Начальный уровень
    )
    # Обновляем профиль, чтобы он был готов к новому упражнению
    await user_bot_profile_service.update_session(
        user_id=db_user.user_id,
        bot_id=BotID.BG,
        exercises_get_in_session=0,
        exercises_get_in_set=0,
        session_started_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        session_frozen_until=None,
    )

    # Act
    next_action = await user_progress_service.get_next_action(
        user_id=db_user.user_id, bot_id=BotID.BG
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
