import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from app.core.entities.user import User
from app.core.entities.user_bot_profile import UserBotProfile
from app.core.enums import LanguageLevel
from app.db.models import DBUserBotProfile as DBUserBotProfileModel
from app.db.models import User as DBUserModel
from app.services.notification_producer import (
    LONG_BREAK_REMINDER_INTERVALS,
    LONG_BREAK_REMINDER_SEQUENCE,
    NotificationProducerService,
    NotificationType,
)
from app.workers.notification_scheduler import (
    NOTIFICATION_SCHEDULER_INTERVAL_SECONDS,
    NotificationScheduler,
)

pytestmark = pytest.mark.asyncio


# --- Фикстуры для NotificationScheduler ---


@pytest.fixture
def mock_notification_producer_service(mocker) -> AsyncMock:
    """Мок для NotificationProducerService."""
    mock = mocker.AsyncMock(spec=NotificationProducerService)
    mock.prepare_and_enqueue_session_reminder = AsyncMock(return_value=True)
    mock.prepare_and_enqueue_long_break_reminder = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_profile_repo_class(mocker) -> MagicMock:
    """Мок для класса репозитория UserBotProfileRepository."""
    mock_repo_instance = mocker.AsyncMock()
    mock_repo_instance.update = AsyncMock(return_value=None)

    # Методы выборки
    mock_repo_instance.get_unfrozen_for_reminder = AsyncMock(return_value=[])
    mock_repo_instance.get_with_long_break_for_reminder = AsyncMock(
        return_value=[]
    )

    mock_class = mocker.MagicMock()
    mock_class.return_value = mock_repo_instance
    return mock_class


@pytest.fixture
def stop_event() -> asyncio.Event:
    """Событие для остановки воркера."""
    return asyncio.Event()


@pytest.fixture
def notification_scheduler(
    stop_event: asyncio.Event,
    mock_notification_producer_service: AsyncMock,
    mock_profile_repo_class: MagicMock,
) -> NotificationScheduler:
    """Экземпляр NotificationScheduler с моками."""
    return NotificationScheduler(
        stop_event=stop_event,
        notification_producer=mock_notification_producer_service,
        profile_repo_class=mock_profile_repo_class,
    )


# --- Тесты для _process_session_reminders ---


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_process_session_reminders_sends_when_conditions_met(
    notification_scheduler: NotificationScheduler,
    mock_notification_producer_service: AsyncMock,
    user: User,
    user_bot_profile: UserBotProfile,
):
    # Arrange
    user_bot_profile.wants_session_reminders = True
    # Сессия стала доступна 1 минуту назад (в пределах окна)
    user_bot_profile.session_frozen_until = datetime.now(
        timezone.utc
    ) - timedelta(minutes=1)

    # Act
    await notification_scheduler._process_session_reminders(
        user, user_bot_profile
    )

    # Assert
    mock_notification_producer_service.prepare_and_enqueue_session_reminder.assert_awaited_once_with(
        user, user_bot_profile
    )


@freeze_time('2023-01-15 12:00:00 UTC')
@pytest.mark.parametrize(
    'wants_reminders, frozen_until_delta_minutes, expect_call',
    [
        (False, -1, False),  # User opted out
        (True, 60, False),  # Session still frozen (1 час в будущем)
        (True, -(NOTIFICATION_SCHEDULER_INTERVAL_SECONDS // 60 + 5), False),
        # Стала доступна слишком давно
        (None, -1, True),  # Wants reminders is None, should send
        (True, None, False),  # session_frozen_until is None
    ],
)
async def test_process_session_reminders_various_conditions(
    notification_scheduler: NotificationScheduler,
    mock_notification_producer_service: AsyncMock,
    user: User,
    user_bot_profile: UserBotProfile,
    wants_reminders: Optional[bool],
    frozen_until_delta_minutes: Optional[int],
    expect_call: bool,
):
    # Arrange
    user_bot_profile.wants_session_reminders = wants_reminders
    if frozen_until_delta_minutes is not None:
        user_bot_profile.session_frozen_until = datetime.now(
            timezone.utc
        ) + timedelta(minutes=frozen_until_delta_minutes)
    else:
        user_bot_profile.session_frozen_until = None

    # Act
    await notification_scheduler._process_session_reminders(
        user, user_bot_profile
    )

    # Assert
    if expect_call:
        mock_notification_producer_service.prepare_and_enqueue_session_reminder.assert_awaited_once_with(
            user, user_bot_profile
        )
    else:
        mock_notification_producer_service.prepare_and_enqueue_session_reminder.assert_not_awaited()


# --- Тесты для _process_long_break_reminders ---


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_process_long_break_no_last_exercise_at(
    notification_scheduler: NotificationScheduler,
    mock_notification_producer_service: AsyncMock,
    mock_profile_repo_class: MagicMock,
    user: User,
    user_bot_profile: UserBotProfile,
    db_session: AsyncMock,  # Используем мок сессии для этого теста
):
    # Arrange
    user_bot_profile.last_exercise_at = None

    # Act
    await notification_scheduler._process_long_break_reminders(
        db_session, user, user_bot_profile
    )

    # Assert
    mock_notification_producer_service.prepare_and_enqueue_long_break_reminder.assert_not_awaited()
    mock_profile_repo_class.return_value.update.assert_not_awaited()


@freeze_time('2023-01-15 12:00:00 UTC')
@pytest.mark.parametrize(
    'days_inactive, last_sent_type, expected_reminder_type, should_send',
    [
        (1, None, None, False),  # Пропустил 1 день, уведомлений не было
        (8, None, '7d', True),  # Пропустил 8 дней, уведомлений не было
        (8, '7d', None, False),  # Пропустил 8 дней, "7d" отправлялось
        (31, '7d', '30d', True),  # Пропустил 31 день, "7d" отправлялось
        (31, None, '30d', True),  # Пропустил 31 день, уведомлений не было
        (100, None, '90d', True),  # Пропустил 100 дней, уведомлений не было
        (100, '30d', '90d', True),  # Пропустил 100 дней, "30d" отправлялось
        (100, '90d', None, False),  # Пропустил 100 дней, "90d" отправлялось
        (5, 'unknown_type', None, False),  # Неизвестный тип, но мало дней
        (60, 'unknown_type', '30d', True),
        # Неизвестный тип, но много дней -> "30d"
        # (т.к. last_sent_type_index будет -1)
    ],
)
async def test_process_long_break_reminders_scenarios(
    notification_scheduler: NotificationScheduler,
    mock_notification_producer_service: AsyncMock,
    mock_profile_repo_class: MagicMock,
    user: User,
    user_bot_profile: UserBotProfile,
    db_session: AsyncMock,  # Мок сессии
    days_inactive: int,
    last_sent_type: Optional[str],
    expected_reminder_type: Optional[str],
    should_send: bool,
):
    # Arrange
    now = datetime.now(timezone.utc)
    user_bot_profile.last_exercise_at = now - timedelta(days=days_inactive)
    user_bot_profile.last_long_break_reminder_type_sent = last_sent_type
    user_bot_profile.last_long_break_reminder_sent_at = (
        now - timedelta(days=1) if last_sent_type else None
    )

    mock_repo_instance = mock_profile_repo_class.return_value
    mock_repo_instance.update.reset_mock()
    mock_notification_producer_service.prepare_and_enqueue_long_break_reminder.reset_mock()

    # Act
    await notification_scheduler._process_long_break_reminders(
        db_session, user, user_bot_profile
    )

    # Assert
    if should_send and expected_reminder_type:
        mock_notification_producer_service.prepare_and_enqueue_long_break_reminder.assert_awaited_once_with(
            user,
            user_bot_profile,
            reminder_type=expected_reminder_type,
            days_inactive=days_inactive,
        )
        mock_repo_instance.update.assert_awaited_once()
        # Проверяем, что данные для обновления корректны
        updated_data_arg = mock_repo_instance.update.call_args[0][0]
        assert (
            updated_data_arg.last_long_break_reminder_type_sent
            == expected_reminder_type
        )
        assert updated_data_arg.last_long_break_reminder_sent_at is not None
    else:
        mock_notification_producer_service.prepare_and_enqueue_long_break_reminder.assert_not_awaited()
        mock_repo_instance.update.assert_not_awaited()


# --- Тесты для run_check_cycle ---


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_run_check_cycle_processes_both_reminder_types(
    notification_scheduler: NotificationScheduler,
    mock_profile_repo_class: MagicMock,  # Используем мок класса репозитория
    user: User,  # Фикстура из conftest.py
    user_bot_profile: UserBotProfile,  # Фикстура из conftest.py
):
    # Arrange
    # Создаем мок DBUserBotProfile, который будет возвращен репозиторием
    db_user = DBUserModel(
        **user.model_dump(exclude={'language_level'}),
        language_level=user.language_level.value,
    )  # Преобразуем Enum

    # Профиль для сессионного напоминания
    db_profile_session = DBUserBotProfileModel(**user_bot_profile.model_dump())
    db_profile_session.user = db_user
    db_profile_session.wants_session_reminders = True
    db_profile_session.session_frozen_until = datetime.now(
        timezone.utc
    ) - timedelta(minutes=1)

    # Профиль для напоминания о долгом перерыве
    user_bot_profile_long_break = user_bot_profile.model_copy(
        update={'user_id': user.user_id + 1 if user.user_id else 2}
    )  # Другой user_id для уникальности
    db_user_long_break = DBUserModel(
        **User(
            user_id=user_bot_profile_long_break.user_id,
            telegram_id='another_tg_id',
        ).model_dump(exclude={'language_level'}),
        language_level=LanguageLevel.A1.value,
    )

    db_profile_long_break = DBUserBotProfileModel(
        **user_bot_profile_long_break.model_dump()
    )
    db_profile_long_break.user = db_user_long_break
    db_profile_long_break.last_exercise_at = datetime.now(
        timezone.utc
    ) - timedelta(days=8)
    db_profile_long_break.last_long_break_reminder_type_sent = None

    mock_repo_instance = mock_profile_repo_class.return_value
    mock_repo_instance.get_unfrozen_for_reminder.return_value = [
        db_profile_session
    ]
    mock_repo_instance.get_with_long_break_for_reminder.return_value = [
        db_profile_long_break
    ]

    # Патчим _process_user_profiles, чтобы проверить вызовы
    with patch.object(
        notification_scheduler,
        '_process_user_profiles',
        new_callable=AsyncMock,
    ) as mock_process_profiles:
        # Патчим async_session_maker, чтобы он возвращал мок сессии
        mock_session = AsyncMock()
        with patch(
            'app.workers.notification_scheduler.async_session_maker',
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(),
            ),
        ):
            # Act
            await notification_scheduler.run_check_cycle()

    # Assert
    mock_repo_instance.get_unfrozen_for_reminder.assert_awaited_once_with(
        NOTIFICATION_SCHEDULER_INTERVAL_SECONDS
    )

    first_reminder_key = LONG_BREAK_REMINDER_SEQUENCE[0]
    expected_min_break_seconds = LONG_BREAK_REMINDER_INTERVALS[
        first_reminder_key
    ].total_seconds()
    mock_repo_instance.get_with_long_break_for_reminder.assert_awaited_once_with(
        min_break_duration_seconds=expected_min_break_seconds
    )

    assert mock_process_profiles.call_count == 2
    # Проверяем вызов для сессионных напоминаний
    mock_process_profiles.assert_any_call(
        profiles=[db_profile_session],
        reminder_type=NotificationType.SESSION_REMINDER,
        session=mock_session,
    )
    # Проверяем вызов для напоминаний о долгом перерыве
    mock_process_profiles.assert_any_call(
        profiles=[db_profile_long_break],
        reminder_type=NotificationType.LONG_BREAK_REMINDER,
        session=mock_session,
    )


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_run_check_cycle_no_profiles_found(
    notification_scheduler: NotificationScheduler,
    mock_profile_repo_class: MagicMock,
):
    # Arrange
    mock_repo_instance = mock_profile_repo_class.return_value
    mock_repo_instance.get_unfrozen_for_reminder.return_value = []
    mock_repo_instance.get_with_long_break_for_reminder.return_value = []

    with patch.object(
        notification_scheduler,
        '_process_user_profiles',
        new_callable=AsyncMock,
    ) as mock_process_profiles:
        mock_session = AsyncMock()
        with patch(
            'app.workers.notification_scheduler.async_session_maker',
            return_value=MagicMock(
                __aenter__=AsyncMock(return_value=mock_session),
                __aexit__=AsyncMock(),
            ),
        ):
            # Act
            await notification_scheduler.run_check_cycle()

    # Assert
    mock_repo_instance.get_unfrozen_for_reminder.assert_awaited_once()
    mock_repo_instance.get_with_long_break_for_reminder.assert_awaited_once()

    # _process_user_profiles будет вызван с пустыми списками
    assert mock_process_profiles.call_count == 2
    mock_process_profiles.assert_any_call(
        profiles=[],
        reminder_type=NotificationType.SESSION_REMINDER,
        session=mock_session,
    )
    mock_process_profiles.assert_any_call(
        profiles=[],
        reminder_type=NotificationType.LONG_BREAK_REMINDER,
        session=mock_session,
    )
