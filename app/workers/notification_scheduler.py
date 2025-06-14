import asyncio
import logging
from datetime import datetime, time, timedelta, timezone
from typing import List, Tuple

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
    NotificationProducerService,
    NotificationType,
)

logger = logging.getLogger(__name__)


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

        if profile.wants_session_reminders is not True:
            return

        if not profile.session_frozen_until:
            return

        window_start_time = now - timedelta(
            seconds=settings.notification_scheduler_interval_seconds
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
                last_sent_type_index = (
                    settings.long_break_reminder_sequence.index(last_sent_type)
                )
            except ValueError:
                logger.warning(
                    f'User {user.user_id} profile {profile.bot_id.value} '
                    f'has unknown last_long_break_reminder_type_sent: '
                    f'{last_sent_type}. '
                    f'Processing all reminder types.'
                )

        reminder_type = None
        possible_reminders = settings.long_break_reminder_sequence[
            last_sent_type_index + 1 :
        ]

        for reminder_key in possible_reminders[::-1]:
            reminder_delta = settings.long_break_reminder_intervals[
                reminder_key
            ]
            if time_since_last_activity >= reminder_delta:
                reminder_type = reminder_key
                break

        if reminder_type:
            if profile.last_long_break_reminder_sent_at:
                min_cooldown_duration = timedelta(
                    hours=settings.long_break_reminders_cooldown_hours
                )
                time_since_last_long_break_sent = (
                    now - profile.last_long_break_reminder_sent_at
                )

                if time_since_last_long_break_sent < min_cooldown_duration:
                    time_since_last_long_break_sent_hours = (
                        time_since_last_long_break_sent.total_seconds() / 3600
                    )
                    logger.info(
                        f'User {user.user_id}, bot_id {profile.bot_id.value} '
                        f"eligible for long break reminder '{reminder_type}',"
                        f' but the previous one '
                        f'was sent too recently at '
                        f'{profile.last_long_break_reminder_sent_at} '
                        f'({time_since_last_long_break_sent_hours:.2f} '
                        f'hours ago). Skipping.'
                    )
                    return

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

        def _get_min_long_break_duration() -> int:
            first_reminder = settings.long_break_reminder_sequence[0]
            result = settings.long_break_reminder_intervals.get(first_reminder)
            if result:
                return int(result.total_seconds())
            else:
                return 0

        def _get_long_reminder_window_time() -> Tuple[time, time]:
            now = datetime.now(timezone.utc)
            current_utc_time = now.time()
            half_window_seconds = (
                settings.long_break_reminder_time_window_seconds / 2
            )
            base_dt_for_window = datetime.combine(now.date(), current_utc_time)

            calculated_window_start = (
                base_dt_for_window - timedelta(seconds=half_window_seconds)
            ).time()
            calculated_window_end = (
                base_dt_for_window + timedelta(seconds=half_window_seconds)
            ).time()
            logger.debug(
                f'Scheduler: Preparing to fetch long break reminders. '
                f'Current UTC time for window: {current_utc_time}. '
                f'Configured window: '
                f'{settings.long_break_reminder_time_window_seconds}. '
                f'Calculated window: '
                f'{calculated_window_start} - {calculated_window_end}'
            )
            return calculated_window_start, calculated_window_end

        logger.info('Notification scheduler: Starting check cycle.')

        async with async_session_maker() as session:
            profile_repo = self.profile_repo_class(session)
            profiles_for_unfreeze_notification = (
                await profile_repo.get_unfrozen_for_reminder(
                    settings.notification_scheduler_interval_seconds
                )
            )
            await self._process_user_profiles(
                profiles=profiles_for_unfreeze_notification,
                reminder_type=NotificationType.SESSION_REMINDER,
                session=session,
            )

            min_break_duration_seconds = _get_min_long_break_duration()
            window_start_time, window_end_time = (
                _get_long_reminder_window_time()
            )
            profiles_for_long_break_notification = (
                await profile_repo.get_with_long_break_for_reminder(
                    min_break_duration_seconds=min_break_duration_seconds,
                    window_start_time=window_start_time,
                    window_end_time=window_end_time,
                )
            )
            await self._process_user_profiles(
                profiles=profiles_for_long_break_notification,
                reminder_type=NotificationType.LONG_BREAK_REMINDER,
                session=session,
            )
            await session.commit()

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
                        timeout=settings.notification_scheduler_interval_seconds,
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
