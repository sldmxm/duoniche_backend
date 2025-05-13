import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.entities.user import User
from app.core.entities.user_bot_profile import (
    UserBotProfile,
)
from app.db.db import async_session_maker
from app.db.models import DBUserBotProfile
from app.db.repositories.user_bot_profile import (
    SQLAlchemyUserBotProfileRepository,
)
from app.services.notification_producer import (
    LONG_BREAK_REMINDER_INTERVALS,
    LONG_BREAK_REMINDER_SEQUENCE,
    NotificationProducerService,
    NotificationType,
)

logger = logging.getLogger(__name__)

NOTIFICATION_SCHEDULER_INTERVAL_SECONDS = 60 * 5


class NotificationScheduler:
    def __init__(
        self,
        stop_event: asyncio.Event,
        notification_producer: NotificationProducerService,
        profile_repo_class=SQLAlchemyUserBotProfileRepository,
    ):
        self.producer = notification_producer
        self.profile_repo_class = profile_repo_class
        self._running = False
        self._stop_event = stop_event

    async def _process_session_reminders(
        self, user: User, profile: UserBotProfile
    ) -> None:
        """
        Checks and enqueues session reminders for a user profile.
        """
        now = datetime.now(timezone.utc)

        if profile.wants_session_reminders is False:
            return

        if not profile.session_frozen_until:
            return

        window_start_time = now - timedelta(
            seconds=NOTIFICATION_SCHEDULER_INTERVAL_SECONDS
        )
        window_end_time = now

        if not (
            window_start_time < profile.session_frozen_until <= window_end_time
        ):
            return

        logger.info(
            f'Attempting to send session reminder to user {user.user_id} '
            f'for bot_id {profile.bot_id.value} '
            f'(session became available recently)'
        )
        success = await self.producer.prepare_and_enqueue_session_reminder(
            user, profile
        )
        if success:
            logger.info(
                f'Session reminder successfully enqueued for user '
                f'{user.user_id}, '
                f'bot_id {profile.bot_id.value}'
            )

    async def _process_long_break_reminders(
        self, session: AsyncSession, user: User, profile: UserBotProfile
    ) -> None:
        """
        Checks and enqueues long break reminders for a user profile.
        """
        now = datetime.now(timezone.utc)
        if not profile.last_exercise_at:
            return

        time_since_last_activity = now - profile.last_exercise_at

        last_sent_type = profile.last_long_break_reminder_type_sent
        last_sent_type_index = -1

        if last_sent_type:
            try:
                last_sent_type_index = LONG_BREAK_REMINDER_SEQUENCE.index(
                    last_sent_type
                )
            except ValueError:
                logger.warning(
                    f'User {user.user_id} profile {profile.bot_id.value} '
                    f'has unknown last_long_break_reminder_type_sent: '
                    f'{last_sent_type}. '
                    f'Processing all reminder types.'
                )

        reminder_type = None
        possible_reminders = LONG_BREAK_REMINDER_SEQUENCE[
            last_sent_type_index + 1 :
        ]

        for reminder_key in possible_reminders[::-1]:
            reminder_delta = LONG_BREAK_REMINDER_INTERVALS[reminder_key]
            if time_since_last_activity >= reminder_delta:
                reminder_type = reminder_key
                break

        if reminder_type:
            logger.info(
                f'User {user.user_id}, bot_id {profile.bot_id.value} '
                f'is inactive for {time_since_last_activity.days} days. '
                f'Attempting to send long break reminder type '
                f"'{reminder_type}'."
            )
            producer = self.producer
            success = await producer.prepare_and_enqueue_long_break_reminder(
                user,
                profile,
                reminder_type=reminder_type,
                days_inactive=time_since_last_activity.days,
            )
            if success:
                logger.info(
                    f"Long break reminder type '{reminder_type}'"
                    f' successfully enqueued '
                    f'for user {user.user_id}, bot_id {profile.bot_id.value}'
                )
                profile_repo = self.profile_repo_class(session)
                updated_profile_data = profile.model_copy(
                    update={
                        'last_long_break_reminder_type_sent': reminder_type,
                        'last_long_break_reminder_sent_at': now,
                    }
                )
                await profile_repo.update(updated_profile_data)

    async def _process_user_profiles(
        self,
        profiles: List[DBUserBotProfile],
        reminder_type: NotificationType,
        session: AsyncSession,
    ):
        processed_users_count = 0
        for profile in profiles:
            user_entity = User.model_validate(profile.user)
            profile_entity = UserBotProfile.model_validate(profile)
            if not user_entity.user_id or not user_entity.telegram_id:
                logger.warning(
                    f'Skipping user with incomplete '
                    f'data: {user_entity.user_id}'
                )
                continue
            try:
                match reminder_type:
                    case NotificationType.SESSION_REMINDER:
                        await self._process_session_reminders(
                            user_entity, profile_entity
                        )
                    case NotificationType.LONG_BREAK_REMINDER:
                        await self._process_long_break_reminders(
                            session, user_entity, profile_entity
                        )

            except Exception as e:
                logger.error(
                    f'Error processing profile {user_entity.user_id}'
                    f'/{profile_entity.bot_id.value} '
                    f'for notifications: {e}',
                    exc_info=True,
                )
            processed_users_count += 1
        logger.info(
            f'Notification scheduler: Processed {processed_users_count} '
            f'{reminder_type.value} notifications.'
        )

    async def run_check_cycle(self) -> None:
        """
        Runs a single cycle of checking and enqueuing notifications.
        """
        logger.info('Notification scheduler: Starting check cycle.')

        async with async_session_maker() as session:
            profile_repo = self.profile_repo_class(session)
            profiles_for_unfreeze_notification = (
                await profile_repo.get_unfrozen_for_reminder(
                    NOTIFICATION_SCHEDULER_INTERVAL_SECONDS
                )
            )
            await self._process_user_profiles(
                profiles=profiles_for_unfreeze_notification,
                reminder_type=NotificationType.SESSION_REMINDER,
                session=session,
            )

            first_reminder = LONG_BREAK_REMINDER_SEQUENCE[0]
            min_break_duration = LONG_BREAK_REMINDER_INTERVALS.get(
                first_reminder
            )
            if min_break_duration:
                min_break_duration_seconds = min_break_duration.total_seconds()
            else:
                min_break_duration_seconds = 0
            profiles_for_long_break_notification = (
                await profile_repo.get_with_long_break_for_reminder(
                    min_break_duration_seconds=min_break_duration_seconds
                )
            )
            await self._process_user_profiles(
                profiles=profiles_for_long_break_notification,
                reminder_type=NotificationType.LONG_BREAK_REMINDER,
                session=session,
            )

        logger.info('Notification scheduler: Check cycle finished.')

    async def start(self) -> None:
        if self._running:
            logger.warning('Notification scheduler is already running.')
            return

        self._running = True
        logger.info('Notification scheduler started.')
        try:
            while self._running:
                try:
                    await self.run_check_cycle()
                except Exception as e:
                    logger.error(
                        f'Unhandled error in notification '
                        f'scheduler main loop: {e}',
                        exc_info=True,
                    )

                if not self._running:
                    break

                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=NOTIFICATION_SCHEDULER_INTERVAL_SECONDS,
                    )
                    logger.info(
                        'Notification scheduler: stop event received '
                        'during sleep interval.'
                    )
                    self._running = False
                    break
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    logger.info(
                        'Notification scheduler: start task cancelled '
                        'during sleep interval.'
                    )
                    self._running = False
                    raise
        finally:
            logger.info('Notification scheduler loop terminated.')
            self._running = False

    def stop(self) -> None:
        logger.info('Notification scheduler stopping...')
        self._running = False


async def notification_scheduler_loop(
    notification_producer: NotificationProducerService,
    stop_event: asyncio.Event,
):
    scheduler = NotificationScheduler(
        notification_producer=notification_producer,
        stop_event=stop_event,
    )
    scheduler_task = asyncio.create_task(
        scheduler.start(), name='NotificationScheduler.start'
    )

    await stop_event.wait()

    scheduler.stop()
    shutdown_wait_timeout = settings.worker_shutdown_timeout_seconds - 0.5
    try:
        await asyncio.wait_for(scheduler_task, timeout=shutdown_wait_timeout)
        logger.info('NotificationScheduler.start task finished gracefully.')
    except asyncio.TimeoutError:
        logger.warning(
            f'NotificationScheduler.start task timed out after '
            f'{shutdown_wait_timeout}s. Cancelling.'
        )
        scheduler_task.cancel()
        try:
            await scheduler_task  # Дать возможность отмене обработаться
        except asyncio.CancelledError:
            logger.info(
                'NotificationScheduler.start task was '
                'effectively cancelled after timeout.'
            )
    except asyncio.CancelledError:
        logger.info('Notification scheduler task was cancelled.')
        if not scheduler_task.done():
            scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            logger.info(
                'Inner scheduler.start() task was cancelled by propagation.'
            )

    logger.info('Notification scheduler loop function finished.')
