import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from app.config import settings
from app.core.configs.enums import (
    ExerciseType,
    LanguageLevel,
    UserAction,
)
from app.core.configs.generation.config import ExerciseTopic
from app.core.configs.texts import Messages, PaymentMessages, get_text
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import (
    NextAction,
)
from app.core.entities.user import User
from app.core.entities.user_bot_profile import (
    UserBotProfile,
    UserStatusInBot,
)
from app.core.entities.user_settings import UserSettings
from app.core.services.exercise import ExerciseService
from app.core.services.payment import (
    INITIATE_PAYMENT_PREFIX,
    SESSION_UNLOCK_PREFIX,
    PaymentService,
)
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.services.user_settings import UserSettingsService
from app.metrics import BACKEND_EXERCISE_METRICS, BACKEND_USER_METRICS

logger = logging.getLogger(__name__)


class UserProgressService:
    def __init__(
        self,
        user_service: UserService,
        exercise_service: ExerciseService,
        user_bot_profile_service: UserBotProfileService,
        payment_service: PaymentService,
        user_settings_service: UserSettingsService,
    ):
        self.user_service = user_service
        self.exercise_service = exercise_service
        self.user_bot_profile_service = user_bot_profile_service
        self.payment_service = payment_service
        self.user_settings_service = user_settings_service

    async def get_next_action(self, user_id: int, bot_id: str) -> NextAction:
        async def _start_new_session() -> UserBotProfile:
            updated_profile = await (
                self.user_bot_profile_service.reset_and_start_new_session(
                    user_id=user_bot_profile.user_id,
                    bot_id=user_bot_profile.bot_id,
                )
            )
            logger.info(f'New session started for user {user_id}/{bot_id}')
            return updated_profile

        # TODO: разобраться, как собирать количество ошибок,
        #  возможно, просто в верификации брать и писать в бд пользователя
        #  ИЛИ !!! вообще убрать эти дополнительные поля у пользователя
        #  и брать все из БД ответов, а у пользователя сохранять
        #  id первого упражнения в сессии

        user: User | None = await self.user_service.get_by_id(user_id)
        if not user or not user.user_id:
            raise ValueError('User with provided ID not found in the database')

        if user.telegram_data:
            user_language = user.telegram_data.get(
                'language_code', settings.default_user_language
            )
        else:
            user_language = settings.default_user_language

        (
            user_bot_profile,
            _,
        ) = await self.user_bot_profile_service.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=user_language,
            language_level=settings.default_language_level,
        )

        if user_bot_profile.status == UserStatusInBot.BLOCKED:
            await self.user_bot_profile_service.mark_user_active(
                user_id=user_bot_profile.user_id,
                bot_id=user_bot_profile.bot_id,
            )
            user_bot_profile.status = UserStatusInBot.ACTIVE
            user_bot_profile.reason = None

        user_settings = (
            await self.user_settings_service.get_effective_settings(
                user_id=user_id, bot_id=bot_id
            )
        )

        now = datetime.now(timezone.utc)
        today_date = now.date()

        new_streak_days = user_bot_profile.current_streak_days
        last_exercise_date = None
        if user_bot_profile.last_exercise_at:
            last_exercise_date = user_bot_profile.last_exercise_at.astimezone(
                timezone.utc
            ).date()

        if last_exercise_date is None:
            new_streak_days = 1
        elif last_exercise_date == today_date:
            pass
        elif last_exercise_date == today_date - timedelta(days=1):
            new_streak_days = user_bot_profile.current_streak_days + 1
        else:
            new_streak_days = 1

        logger.info(
            f'Exercise in session user {user_id}: '
            f' {user_bot_profile.exercises_get_in_session}'
        )

        if user_bot_profile.session_frozen_until is not None:
            if now < user_bot_profile.session_frozen_until:
                logger.info(
                    f'User {user.user_id} is frozen until '
                    f'{user_bot_profile.session_frozen_until}, {now=}'
                )
                BACKEND_USER_METRICS['frozen_attempts'].labels(
                    cohort=user.cohort,
                    plan=user.plan,
                    target_language=user_bot_profile.bot_id,
                    user_language=user_bot_profile.user_language,
                    language_level=user_bot_profile.language_level.value,
                ).inc()

                delta_to_next_session = str(
                    user_bot_profile.session_frozen_until - now
                ).split('.')[0]

                payment_button_text = get_text(
                    PaymentMessages.BUTTON_TEXT, user_bot_profile.user_language
                )
                payment_button_callback_data = (
                    f'{INITIATE_PAYMENT_PREFIX}:{SESSION_UNLOCK_PREFIX}'
                )

                return NextAction(
                    action=UserAction.limit_reached,
                    message=get_text(
                        Messages.LIMIT_REACHED,
                        language_code=user_bot_profile.user_language,
                        pause_time=delta_to_next_session,
                    ),
                    keyboard=[
                        {
                            'text': payment_button_text,
                            'callback_data': payment_button_callback_data,
                        },
                    ],
                )
            else:
                logger.info(
                    f'User {user.user_id} WAS frozen '
                    f'until {user_bot_profile.session_frozen_until}, {now=}'
                )
                user_bot_profile = await _start_new_session()

        if user_bot_profile.session_started_at is None:
            logger.info(f'New user {user.user_id} first session started')
            user_bot_profile = await _start_new_session()
            current_session_time = timedelta(0)
        else:
            current_session_time = now - user_bot_profile.session_started_at

        if current_session_time > settings.max_sessions_length:
            user_bot_profile = await _start_new_session()

        if (
            user_bot_profile.exercises_get_in_session
            >= user_settings.session_exercise_limit
        ):
            session_pause = timedelta(
                minutes=user_settings.min_session_interval_minutes
            )
            user_bot_profile = (
                await self.user_bot_profile_service.update_session(
                    user_id=user.user_id,
                    bot_id=bot_id,
                    session_frozen_until=now + session_pause,
                    wants_session_reminders=None,
                )
            )

            BACKEND_USER_METRICS['full_sessions'].labels(
                cohort=user.cohort,
                plan=user.plan,
                target_language=user_bot_profile.bot_id,
                user_language=user_bot_profile.user_language,
                language_level=user_bot_profile.language_level.value,
            ).inc()

            logger.info(
                f'User {user_id} ended session and is frozen. '
                f'Current streak: {user_bot_profile.current_streak_days} days.'
            )

            message_key: Messages
            message_kwargs: dict[str, Any] = {
                'exercise_num': user_bot_profile.exercises_get_in_session,
                'pause_time': str(session_pause).split('.')[0],
            }

            if user_bot_profile.current_streak_days >= 2:
                message_key = Messages.CONGRATULATIONS_AND_WAIT_STREAK
                message_kwargs['streak_days'] = (
                    user_bot_profile.current_streak_days
                )
            else:
                message_key = Messages.CONGRATULATIONS_AND_WAIT

            payment_button_text = get_text(
                PaymentMessages.BUTTON_TEXT, user_bot_profile.user_language
            )
            payment_button_callback_data = (
                f'{INITIATE_PAYMENT_PREFIX}:{SESSION_UNLOCK_PREFIX}'
            )
            return NextAction(
                action=UserAction.congratulations_and_wait,
                message=get_text(
                    message_key,
                    language_code=user_bot_profile.user_language,
                    **message_kwargs,
                ),
                pause=session_pause,
                keyboard=[
                    {
                        'text': payment_button_text,
                        'callback_data': payment_button_callback_data,
                    },
                ],
            )

        if (
            user_bot_profile.exercises_get_in_set
            < user_settings.exercises_in_set
        ):
            try:
                next_exercise = await self._get_next_exercise(
                    user_id=user.user_id,
                    target_language=user_bot_profile.bot_id,
                    user_language=user_bot_profile.user_language,
                    language_level=user_bot_profile.language_level,
                    user_settings=user_settings,
                )
            except ValueError as e:
                logger.error(f'Error getting new exercise: {e}')
                return NextAction(
                    action=UserAction.error,
                    message=get_text(
                        Messages.ERROR_GETTING_NEW_EXERCISE,
                        user_bot_profile.user_language,
                    ),
                )
            user_bot_profile = await (
                self.user_bot_profile_service.update_session(
                    user_id=user.user_id,
                    bot_id=bot_id,
                    exercises_get_in_session=(
                        user_bot_profile.exercises_get_in_session + 1
                    ),
                    exercises_get_in_set=(
                        user_bot_profile.exercises_get_in_set + 1
                    ),
                    last_exercise_at=now,
                    last_long_break_reminder_type_sent=None,
                    last_long_break_reminder_sent_at=None,
                    current_streak_days=new_streak_days,
                )
            )

            BACKEND_EXERCISE_METRICS['sent'].labels(
                exercise_type=next_exercise.exercise_type.value,
                level=next_exercise.language_level.value,
            ).inc()

            return NextAction(
                exercise=next_exercise,
                action=UserAction.new_exercise,
            )
        else:
            user_bot_profile = (
                await self.user_bot_profile_service.update_session(
                    user_id=user.user_id,
                    bot_id=bot_id,
                    exercises_get_in_set=0,
                    errors_count_in_set=0,
                )
            )

            return NextAction(
                action=UserAction.praise_and_next_set,
                message=get_text(
                    Messages.PRAISE_AND_NEXT_SET,
                    user_bot_profile.user_language,
                ),
            )

    async def _get_next_exercise(
        self,
        user_id: int,
        target_language: str,
        user_language: str,
        language_level: LanguageLevel,
        user_settings: UserSettings,
    ) -> Exercise:
        language_level = LanguageLevel.get_next_exercise_level(language_level)
        logger.debug(
            f'Next exercise level: {language_level} ' f'for user {user_id}'
        )

        topic = ExerciseTopic.get_topic(
            exclude_topics=user_settings.exclude_topics
        )

        distribution = user_settings.exercise_type_distribution

        if not distribution:
            logger.error(
                f'Exercise type distribution not found for user {user_id}'
            )
            distribution = {
                ex_type: 1 / len(ExerciseType) for ex_type in ExerciseType
            }

        population = list(distribution.keys())
        weights = list(distribution.values())
        exercise_type = random.choices(population=population, weights=weights)[
            0
        ]

        logger.info(
            f'Next exercise topic: {topic.value}, exercise type '
            f'{exercise_type.value} for user'
            f' {user_id}'
        )

        exercise = await self.exercise_service.get_next_exercise(
            user_id=user_id,
            target_language=target_language,
            user_language=user_language,
            exercise_type=exercise_type,
            topic=topic,
            language_level=language_level,
        )

        if not exercise:
            logger.warning(
                f'No suitable exercise found for user {user_id} '
                f'with criteria: '
                f'type={exercise_type.value}, '
                f'topic={topic.value}, '
                f'level={language_level.value}'
            )
            raise ValueError(
                'No suitable exercise found for the provided criteria'
            )

        return exercise
