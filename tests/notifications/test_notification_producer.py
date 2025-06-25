from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from freezegun import freeze_time

from app.celery_producer import NOTIFIER_TASK_NAME, notifier_celery_producer
from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import UserBotProfile
from app.core.enums import LanguageLevel
from app.services.notification_producer import (
    NotificationProducerService,
    NotificationTaskData,
    NotificationType,
    TelegramMessagePayload,
)

pytestmark = pytest.mark.asyncio


# --- Фикстуры для NotificationProducerService ---


@pytest.fixture
def producer() -> NotificationProducerService:
    """Экземпляр NotificationProducerService."""
    return NotificationProducerService()


@pytest.fixture
def sample_user(user: User) -> User:
    """Пример пользователя для тестов."""
    if user.user_id is None:
        user.user_id = 123
    if not isinstance(user.telegram_id, str) or not user.telegram_id.isdigit():
        user.telegram_id = '123456789'
    return user


@pytest.fixture
def sample_user_bot_profile(
    user_bot_profile: UserBotProfile, sample_user: User
) -> UserBotProfile:
    """Пример профиля пользователя для тестов."""
    user_bot_profile.user_id = sample_user.user_id
    user_bot_profile.bot_id = 'Bulgarian'
    user_bot_profile.user_language = 'ru'
    user_bot_profile.language_level = LanguageLevel.A2
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
        user_id=sample_user.user_id,
        bot_id=sample_user_bot_profile.bot_id,
        text='Test notification text',
        notification_type=NotificationType.SESSION_REMINDER,
        payload=sample_telegram_payload,
        metadata={},
        scheduled_at=None,
    )


@pytest.fixture
def mock_backend_notification_metrics(mocker):
    """
    Fixture to mock the BACKEND_NOTIFICATION_METRICS dictionary
    and provide the mocked metrics to tests.
    """
    mocked_metrics = {
        'enqueue_attempt_total': MagicMock(),
        'enqueue_success_total': MagicMock(),
        'enqueue_failure_total': MagicMock(),
        'enqueue_duration_seconds': MagicMock(),
    }
    mocker.patch.dict(
        'app.metrics.BACKEND_NOTIFICATION_METRICS', mocked_metrics, clear=True
    )
    return mocked_metrics


# --- Тесты для enqueue_notification ---


@patch.object(notifier_celery_producer, 'send_task', new_callable=MagicMock)
async def test_enqueue_notification_success(
    mock_send_task: MagicMock,
    mock_backend_notification_metrics: dict,
    producer: NotificationProducerService,
    sample_notification_task_data: NotificationTaskData,
):
    # Arrange
    mock_duration_metric = MagicMock()
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.return_value.__enter__.return_value = (
        mock_duration_metric
    )
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.return_value.__exit__.return_value = None

    # Act
    success = await producer.enqueue_notification(
        sample_notification_task_data
    )

    # Assert
    assert success is True

    mock_send_task.assert_called_once_with(
        NOTIFIER_TASK_NAME,
        args=[sample_notification_task_data.model_dump()],
        queue=settings.notification_tasks_queue_name,
        task_id=sample_notification_task_data.task_id,
        # eta=...
    )

    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_success_total'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_success_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_failure_total'
    ].labels.assert_not_called()

    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.assert_called_once()


@patch('app.services.notification_producer.NotificationTaskData.model_dump')
@patch.object(notifier_celery_producer, 'send_task', new_callable=MagicMock)
async def test_enqueue_notification_arg_preparation_error(
    mock_send_task: MagicMock,
    mock_model_dump: MagicMock,
    mock_backend_notification_metrics: dict,
    producer: NotificationProducerService,
    sample_notification_task_data: NotificationTaskData,
):
    # Arrange
    mock_model_dump.side_effect = TypeError('Argument preparation failed')

    # Act
    success = await producer.enqueue_notification(
        sample_notification_task_data
    )

    # Assert
    assert success is False
    mock_send_task.assert_not_called()

    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_success_total'
    ].labels.assert_not_called()

    mock_backend_notification_metrics[
        'enqueue_failure_total'
    ].labels.assert_called_once_with(
        reason='arg_preparation_error',
        notification_type=sample_notification_task_data.notification_type.value,
    )
    mock_backend_notification_metrics[
        'enqueue_failure_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.assert_not_called()


@patch.object(notifier_celery_producer, 'send_task', new_callable=MagicMock)
async def test_enqueue_notification_celery_send_error(
    mock_send_task: MagicMock,
    mock_backend_notification_metrics: dict,
    producer: NotificationProducerService,
    sample_notification_task_data: NotificationTaskData,
):
    # Arrange
    mock_duration_metric = MagicMock()
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.return_value.__enter__.return_value = (
        mock_duration_metric
    )
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.return_value.__exit__.return_value = None

    mock_send_task.side_effect = Exception('Celery broker connection failed')

    # Act
    success = await producer.enqueue_notification(
        sample_notification_task_data
    )

    # Assert
    assert success is False

    mock_send_task.assert_called_once_with(
        NOTIFIER_TASK_NAME,
        args=[sample_notification_task_data.model_dump()],
        queue=settings.notification_tasks_queue_name,
        task_id=sample_notification_task_data.task_id,
        # eta=...
    )

    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_attempt_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_success_total'
    ].labels.assert_not_called()

    mock_backend_notification_metrics[
        'enqueue_failure_total'
    ].labels.assert_called_once_with(
        reason='celery_send_error',
        notification_type=sample_notification_task_data.notification_type.value,
    )
    mock_backend_notification_metrics[
        'enqueue_failure_total'
    ].labels.return_value.inc.assert_called_once()

    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.assert_called_once_with(
        notification_type=sample_notification_task_data.notification_type.value
    )
    mock_backend_notification_metrics[
        'enqueue_duration_seconds'
    ].labels.return_value.time.assert_called_once()


# --- Тесты для prepare_and_enqueue_session_reminder ---


@freeze_time('2023-01-15 12:00:00 UTC')
async def test_prepare_session_reminder_success(
    producer: NotificationProducerService,
    sample_user: User,
    sample_user_bot_profile: UserBotProfile,
):
    # Arrange
    sample_user_bot_profile.wants_session_reminders = True
    sample_user_bot_profile.session_frozen_until = None

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
        '🚀готовы прокачаться? новая сессия уже доступна '
        in called_task_data.text.lower()
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
    reminder_type = '5d'
    days_inactive = 5

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
        'лучшее время посадить дерево было 20 лет назад'
        in called_task_data.text.lower()
        or 'best time to plant a tree' in called_task_data.text.lower()
    )
    assert called_task_data.metadata is not None
    assert called_task_data.metadata.get('reminder_type') == reminder_type
    assert called_task_data.metadata.get('days_inactive') == days_inactive
