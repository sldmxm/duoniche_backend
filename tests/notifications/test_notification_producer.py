from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time
from redis.exceptions import RedisError

from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.services.notification_producer import (
    NotificationProducerService,
    NotificationTaskData,
    NotificationType,
    TelegramMessagePayload,
)

pytestmark = pytest.mark.asyncio


# --- Фикстуры для NotificationProducerService ---


@pytest.fixture
def mock_redis_client(mocker) -> AsyncMock:
    """Мок для AsyncRedis клиента."""
    mock = mocker.AsyncMock(spec_set=['rpush'])
    mock.rpush = AsyncMock(return_value=1)
    return mock


@pytest.fixture
def producer(
    mock_redis_client: AsyncMock,
) -> NotificationProducerService:
    """Экземпляр NotificationProducerService с моком Redis."""
    return NotificationProducerService(redis_client=mock_redis_client)


@pytest.fixture
def sample_user(user: User) -> User:  # Используем фикстуру user из conftest.py
    """Пример пользователя для тестов."""
    # Убедимся, что user_id и telegram_id имеют значения для тестов продюсера
    if user.user_id is None:
        user.user_id = 123
    if not isinstance(user.telegram_id, str) or not user.telegram_id.isdigit():
        user.telegram_id = '123456789'  # Telegram ID должен быть строкой цифр
    return user


@pytest.fixture
def sample_user_bot_profile(
    user_bot_profile: UserBotProfile, sample_user: User
) -> UserBotProfile:  # Используем фикстуру user_bot_profile из conftest.py
    """Пример профиля пользователя для тестов."""
    user_bot_profile.user_id = sample_user.user_id  # Связываем с sample_user
    user_bot_profile.bot_id = BotID.BG
    user_bot_profile.user_language = 'ru'
    return user_bot_profile


@pytest.fixture
def sample_telegram_payload(sample_user: User) -> TelegramMessagePayload:
    return TelegramMessagePayload(
        telegram_id=int(sample_user.telegram_id),
        parse_mode='HTML',
        reply_markup=None,
        disable_web_page_preview=True,
    )


@pytest.fixture
def sample_notification_task_data(
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
    sample_telegram_payload: TelegramMessagePayload,
) -> NotificationTaskData:
    """Пример валидных данных для задачи уведомления."""
    return NotificationTaskData(
        user_id=sample_user.user_id,  # sample_user.user_id уже int
        bot_id=sample_user_bot_profile.bot_id,
        text='Test notification text',
        notification_type=NotificationType.SESSION_REMINDER,
        payload=sample_telegram_payload,
        metadata={},
        scheduled_at=None,
    )


# --- Тесты для enqueue_notification ---


async def test_enqueue_notification_success(
    producer: NotificationProducerService,
    mock_redis_client: AsyncMock,
    sample_notification_task_data: NotificationTaskData,
):
    # Act
    success = await producer.enqueue_notification(
        sample_notification_task_data
    )

    # Assert
    assert success is True
    mock_redis_client.rpush.assert_awaited_once_with(
        settings.notification_tasks_queue_name,
        sample_notification_task_data.model_dump_json().encode('utf-8'),
    )


@patch(
    'app.services.notification_producer.NotificationTaskData.model_dump_json'
)
async def test_enqueue_notification_serialization_error(
    mock_model_dump_json: MagicMock,
    producer: NotificationProducerService,
    mock_redis_client: AsyncMock,
    sample_notification_task_data: NotificationTaskData,
):
    # Arrange
    mock_model_dump_json.side_effect = TypeError('Serialization failed')

    # Act
    success = await producer.enqueue_notification(
        sample_notification_task_data
    )

    # Assert
    assert success is False
    mock_redis_client.rpush.assert_not_awaited()


async def test_enqueue_notification_redis_error_after_retries(
    producer: NotificationProducerService,
    mock_redis_client: AsyncMock,
    sample_notification_task_data: NotificationTaskData,
):
    # Arrange
    mock_redis_client.rpush.side_effect = RedisError('Connection failed')

    with patch('tenacity.wait.wait_exponential') as mock_wait_exponential:
        mock_wait_exponential.return_value.wait = AsyncMock(
            return_value=0.001
        )  # Например, 1 миллисекунда

        # Act
        success = await producer.enqueue_notification(
            sample_notification_task_data
        )

    # Assert
    assert success is False
    assert mock_redis_client.rpush.await_count == 5


# --- Тесты для prepare_and_enqueue_session_reminder ---


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_prepare_session_reminder_success(
    producer: NotificationProducerService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Arrange
    sample_user_bot_profile.wants_session_reminders = True
    sample_user_bot_profile.session_frozen_until = None  # Сессия не заморожена

    with patch.object(
        producer,
        'enqueue_notification',
        new_callable=AsyncMock,
    ) as mock_enqueue:
        mock_enqueue.return_value = True
        # Act
        success = await producer.prepare_and_enqueue_session_reminder(
            sample_user, sample_user_bot_profile
        )

    # Assert
    assert success is True
    mock_enqueue.assert_awaited_once()
    called_task_data: NotificationTaskData = mock_enqueue.call_args[0][0]
    assert called_task_data.user_id == sample_user.user_id
    assert called_task_data.bot_id == sample_user_bot_profile.bot_id
    assert (
        called_task_data.notification_type == NotificationType.SESSION_REMINDER
    )
    assert called_task_data.payload.telegram_id == int(sample_user.telegram_id)
    assert (
        'сессия упражнений' in called_task_data.text.lower()
        or 'exercise session' in called_task_data.text.lower()
    )


async def test_prepare_session_reminder_user_does_not_want(
    producer: NotificationProducerService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Arrange
    sample_user_bot_profile.wants_session_reminders = False
    with patch.object(
        producer,
        'enqueue_notification',
        new_callable=AsyncMock,
    ) as mock_enqueue:
        # Act
        success = await producer.prepare_and_enqueue_session_reminder(
            sample_user, sample_user_bot_profile
        )

    # Assert
    assert success is False
    mock_enqueue.assert_not_awaited()


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_prepare_session_reminder_session_frozen(
    producer: NotificationProducerService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Arrange
    sample_user_bot_profile.wants_session_reminders = True
    sample_user_bot_profile.session_frozen_until = datetime.now(
        timezone.utc
    ) + timedelta(hours=1)

    with patch.object(
        producer,
        'enqueue_notification',
        new_callable=AsyncMock,
    ) as mock_enqueue:
        # Act
        success = await producer.prepare_and_enqueue_session_reminder(
            sample_user, sample_user_bot_profile
        )

    # Assert
    assert success is False
    mock_enqueue.assert_not_awaited()


# --- Тесты для prepare_and_enqueue_long_break_reminder ---


async def test_prepare_long_break_reminder_success(
    producer: NotificationProducerService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Arrange
    reminder_type = '7d'
    days_inactive = 8

    with patch.object(
        producer,
        'enqueue_notification',
        new_callable=AsyncMock,
    ) as mock_enqueue:
        mock_enqueue.return_value = True
        # Act
        success = await producer.prepare_and_enqueue_long_break_reminder(
            sample_user, sample_user_bot_profile, reminder_type, days_inactive
        )

    # Assert
    assert success is True
    mock_enqueue.assert_awaited_once()
    called_task_data: NotificationTaskData = mock_enqueue.call_args[0][0]
    assert called_task_data.user_id == sample_user.user_id
    assert called_task_data.bot_id == sample_user_bot_profile.bot_id
    assert (
        called_task_data.notification_type
        == NotificationType.LONG_BREAK_REMINDER
    )
    assert called_task_data.payload.telegram_id == int(sample_user.telegram_id)
    assert (
        'не заходил' in called_task_data.text.lower()
        or "haven't been active" in called_task_data.text.lower()
    )
    assert called_task_data.metadata is not None
    assert called_task_data.metadata.get('reminder_type') == reminder_type
    assert called_task_data.metadata.get('days_inactive') == days_inactive
