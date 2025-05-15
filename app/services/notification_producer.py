import logging
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, Optional, cast

from pydantic import BaseModel, Field, field_validator

from app.celery_producer import NOTIFIER_TASK_NAME, notifier_celery_producer
from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import BotID, UserBotProfile
from app.metrics import BACKEND_NOTIFICATION_METRICS

logger = logging.getLogger(__name__)

LONG_BREAK_REMINDER_INTERVALS: Dict[str, timedelta] = {
    '7d': timedelta(days=7),
    '30d': timedelta(days=30),
    '90d': timedelta(days=90),
}
LONG_BREAK_REMINDER_SEQUENCE = ['7d', '30d', '90d']
# SESSION_REMINDER_COOLDOWN = timedelta(hours=1)


class NotificationType(str, Enum):
    SESSION_REMINDER = 'session_reminder'
    LONG_BREAK_REMINDER = 'long_break_reminder'
    # STREAK_REMINDER = "streak_reminder"
    # CUSTOM_BROADCAST = "custom_broadcast"


class TelegramMessagePayload(BaseModel):
    telegram_id: int = Field(..., description='Telegram User ID for targeting')
    parse_mode: Optional[str] = Field(
        None, description='Parse mode for the message (HTML, MarkdownV2)'
    )
    reply_markup: Optional[Dict[str, Any]] = Field(
        None, description='Keyboard for the message (JSON dict)'
    )
    disable_web_page_preview: Optional[bool] = Field(
        None, description='Disable web page preview'
    )

    @classmethod
    @field_validator('parse_mode')
    def validate_parse_mode(cls, v: Optional[str]) -> Optional[str]:
        if v and v not in ['HTML', 'MarkdownV2']:
            raise ValueError('Invalid parse_mode. Must be HTML or MarkdownV2')
        return v


class NotificationTaskData(BaseModel):
    """
    Data model for the task of sending a notification received from Redis.
    Validates the structure and data types of the task.
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description='Unique ID of the task',
    )
    bot_id: BotID = Field(
        ...,
        description='Bot (language) identifier, determines '
        'which bot sends the message',
    )
    user_id: int = Field(..., description='User ID')
    text: str = Field(..., description='Notification text')
    notification_type: NotificationType = Field(
        ..., description='Type of the notification'
    )
    payload: TelegramMessagePayload = Field(
        ...,
        description='Payload specific to the notification '
        'channel (e.g., Telegram)',
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None, description='Additional metadata for the task'
    )
    scheduled_at: Optional[datetime] = Field(
        None,
        description='Time when the notification should '
        'ideally be sent (UTC)',
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description='Timestamp of task creation',
    )


class NotificationProducerService:
    """
    Service responsible for preparing
    and enqueuing notification tasks to Redis.
    """

    def __init__(self):
        self.celery_producer = notifier_celery_producer
        self.queue_name = settings.notification_tasks_queue_name

    async def enqueue_notification(
        self, task_data: NotificationTaskData
    ) -> bool:
        """
        Prepares and enqueues a notification task to the Redis queue.

        Args:
            task_data: The data for the notification task.

        Returns:
            True if the task was successfully enqueued after retries,
            False otherwise.
        """
        BACKEND_NOTIFICATION_METRICS['enqueue_attempt_total'].labels(
            notification_type=task_data.notification_type.value
        ).inc()

        try:
            task_args = [task_data.model_dump()]
            logger.debug(
                f'Preparing task {task_data.task_id} args for Celery.'
            )

        except Exception as e:
            logger.error(
                f'Failed to prepare arguments for notification task '
                f'{task_data.task_id}: {e}',
                exc_info=True,
            )

            BACKEND_NOTIFICATION_METRICS['enqueue_failure_total'].labels(
                reason='arg_preparation_error',
                notification_type=task_data.notification_type.value,
            ).inc()
            return False

        try:
            with (
                BACKEND_NOTIFICATION_METRICS['enqueue_duration_seconds']
                .labels(notification_type=task_data.notification_type.value)
                .time()
            ):
                self.celery_producer.send_task(
                    NOTIFIER_TASK_NAME,
                    args=task_args,
                    queue=self.queue_name,
                    task_id=task_data.task_id,
                    # eta=task_data.scheduled_at
                )

            BACKEND_NOTIFICATION_METRICS['enqueue_success_total'].labels(
                notification_type=task_data.notification_type.value
            ).inc()
            logger.info(
                f'Notification task {task_data.task_id} '
                f'successfully enqueued via Celery.'
            )
            return True

        except Exception as e:
            logger.error(
                f'Failed to enqueue notification task {task_data.task_id} '
                f' via Celery: {e}',
                exc_info=True,
            )
            BACKEND_NOTIFICATION_METRICS['enqueue_failure_total'].labels(
                reason='celery_send_error',
                notification_type=task_data.notification_type.value,
            ).inc()
            return False

    def _get_session_reminder_text(self, user_profile: UserBotProfile) -> str:
        # TODO: Реализовать получение текста из системы шаблонов
        #  на основе user_profile.user_language
        if user_profile.user_language.lower().startswith('ru'):
            return 'Привет! Новая сессия упражнений ждет тебя. Начнем?'
        return (
            'Hello! A new exercise session is waiting for you. '
            'Shall we start?'
        )

    async def prepare_and_enqueue_session_reminder(
        self, user: User, user_profile: UserBotProfile
    ) -> bool:
        """
        Prepares and enqueues a session reminder if conditions are met.
        - User wants session reminders.
        - Session is not frozen.
        - A reminder hasn't been sent recently (cooldown).
        """
        if user_profile.wants_session_reminders is False:
            logger.debug(
                f'User {user.user_id} (profile bot_id {user_profile.bot_id}) '
                f'does not want session reminders. Skipping.'
            )
            return False

        now = datetime.now(timezone.utc)
        if (
            user_profile.session_frozen_until
            and user_profile.session_frozen_until > now
        ):
            logger.debug(
                f'User {user.user_id} (profile bot_id {user_profile.bot_id}) '
                f'session is still frozen until '
                f'{user_profile.session_frozen_until}. '
                f'Skipping session reminder.'
            )
            return False

        text = self._get_session_reminder_text(user_profile)
        task_data = NotificationTaskData(
            user_id=cast(int, user.user_id),
            bot_id=user_profile.bot_id,
            text=text,
            notification_type=NotificationType.SESSION_REMINDER,
            payload=TelegramMessagePayload(
                telegram_id=int(user.telegram_id),
                parse_mode='HTML',
                reply_markup=None,
                disable_web_page_preview=True,
            ),
            metadata={},
            scheduled_at=None,
        )
        logger.info(
            f'Preparing session reminder for user {user.user_id}, '
            f'profile bot_id {user_profile.bot_id}.'
        )
        return await self.enqueue_notification(task_data)

    def _get_long_break_reminder_text(
        self,
        user_profile: UserBotProfile,
        reminder_type: str,
        days_inactive: int,
    ) -> str:
        # TODO: Реализовать получение текста из системы шаблонов
        if user_profile.user_language.lower().startswith('ru'):
            return (
                f'Привет! Мы заметили, что ты не заходил '
                f'уже {days_inactive} дней. Возвращайся к упражнениям!'
            )
        return (
            f"Hello! We've noticed you haven't been "
            f'active for {days_inactive} days. Come back and practice!'
        )

    async def prepare_and_enqueue_long_break_reminder(
        self,
        user: User,
        user_profile: UserBotProfile,
        reminder_type: str,
        days_inactive: int,
    ) -> bool:
        """
        Prepares and enqueues a long break reminder.
        """
        text = self._get_long_break_reminder_text(
            user_profile, reminder_type, days_inactive
        )
        task_data = NotificationTaskData(
            user_id=cast(int, user.user_id),
            bot_id=user_profile.bot_id,
            text=text,
            notification_type=NotificationType.LONG_BREAK_REMINDER,
            payload=TelegramMessagePayload(
                telegram_id=int(user.telegram_id),
                parse_mode='HTML',
                reply_markup=None,
                disable_web_page_preview=True,
            ),
            metadata={
                'reminder_type': reminder_type,
                'days_inactive': days_inactive,
            },
            scheduled_at=None,
        )
        logger.info(
            f'Preparing long break reminder (type: {reminder_type}) '
            f'for user {user.user_id}, profile bot_id {user_profile.bot_id}.'
        )
        return await self.enqueue_notification(task_data)

    # Пример для кастомной рассылки (если понадобится в будущем)
    # async def prepare_and_enqueue_custom_broadcast(
    #     self,
    #     user: User,
    #     user_profile: UserBotProfile, # Для user_language и bot_id
    #     text: str,
    #     # ... другие параметры, например, parse_mode, reply_markup ...
    # ) -> bool:
    #     task_data = NotificationTaskData(
    #         user_id=user.user_id,
    #         telegram_id=user.telegram_id,
    #         bot_id=user_profile.bot_id,
    #         notification_type=NotificationType.CUSTOM_BROADCAST,
    #         payload=TelegramMessagePayload(text=text),
    #         # metadata можно использовать для доп. информации о рассылке
    #     )
    #     logger.info(
    #         f"Preparing custom broadcast for user {user.user_id}, "
    #         f"profile bot_id {user_profile.bot_id}."
    #     )
    #     return await self.enqueue_notification(task_data)
