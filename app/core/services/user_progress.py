import logging
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.entities.user_bot_profile import (
    BotID,
    UserBotProfile,
    UserStatusInBot,
)
from app.core.enums import (
    ExerciseTopic,
    ExerciseType,
    LanguageLevel,
    UserAction,
)
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.services.user_bot_profile import UserBotProfileService
from app.core.texts import Messages, get_text
from app.metrics import BACKEND_EXERCISE_METRICS, BACKEND_USER_METRICS

logger = logging.getLogger(__name__)


class UserProgressService:
    def __init__(
        self,
        user_service: UserService,
        exercise_service: ExerciseService,
        user_bot_profile_service: UserBotProfileService,
    ):
        self.user_service = user_service
        self.exercise_service = exercise_service
        self.user_bot_profile_service = user_bot_profile_service

    async def get_next_action(self, user_id: int, bot_id: BotID) -> NextAction:
        async def _start_new_session() -> UserBotProfile:
            if not user_bot_profile:
                raise ValueError(
                    'User with provided ID not found in the database'
                )
            return await self.user_bot_profile_service.update_session(
                user_id=user_bot_profile.user_id,
                bot_id=user_bot_profile.bot_id,
                exercises_get_in_session=0,
                exercises_get_in_set=0,
                errors_count_in_set=0,
                session_started_at=now,
                session_frozen_until=None,
                wants_session_reminders=None,
                last_long_break_reminder_type_sent=None,
                last_long_break_reminder_sent_at=None,
            )

        # TODO: разобраться, как собирать количество ошибок,
        #  возможно, просто в верификации брать и писать в бд пользователя
        #  ИЛИ !!! вообще убрать эти дополнительные поля у пользователя
        #  и брать все из БД ответов, а у пользователя сохранять
        #  id первого упражнения в сессии

        user: User | None = await self.user_service.get_by_id(user_id)
        if not user or not user.user_id:
            raise ValueError('User with provided ID not found in the database')
        (
            user_bot_profile,
            _,
        ) = await self.user_bot_profile_service.get_or_create(
            user_id=user_id,
            bot_id=bot_id,
            user_language=settings.default_user_language,
            language_level=settings.default_language_level,
        )

        if user_bot_profile.status == UserStatusInBot.BLOCKED:
            await self.user_bot_profile_service.mark_user_active(
                user_id=user_bot_profile.user_id,
                bot_id=user_bot_profile.bot_id,
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

                return NextAction(
                    action=UserAction.limit_reached,
                    message=get_text(
                        Messages.LIMIT_REACHED,
                        language_code=user_bot_profile.user_language,
                        pause_time=delta_to_next_session,
                    ),
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
            current_session_time = timedelta(0)

        renewed_sets = int(
            current_session_time.total_seconds()
            // settings.renewing_set_period.total_seconds()
        )
        current_set_limit = max(settings.sets_in_session, renewed_sets)
        current_exercises_limit = current_set_limit * settings.exercises_in_set

        if (
            current_exercises_limit - user_bot_profile.exercises_get_in_session
            <= 0
        ):
            user_bot_profile = (
                await self.user_bot_profile_service.update_session(
                    user_id=user.user_id,
                    bot_id=bot_id,
                    session_frozen_until=now + settings.delta_between_sessions,
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

            return NextAction(
                action=UserAction.congratulations_and_wait,
                message=get_text(
                    Messages.CONGRATULATIONS_AND_WAIT,
                    language_code=user_bot_profile.user_language,
                    exercise_num=user_bot_profile.exercises_get_in_session,
                    pause_time=str(settings.delta_between_sessions).split('.')[
                        0
                    ],
                ),
                pause=settings.delta_between_sessions,
            )

        if user_bot_profile.exercises_get_in_set < settings.exercises_in_set:
            try:
                next_exercise = await self._get_next_exercise(
                    user_id=user.user_id,
                    target_language=user_bot_profile.bot_id.value,
                    user_language=user_bot_profile.user_language,
                    language_level=user_bot_profile.language_level,
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
            profile_service = self.user_bot_profile_service
            user_bot_profile.exercises_get_in_session += 1
            user_bot_profile.exercises_get_in_set += 1
            user_bot_profile = await profile_service.update_session(
                user_id=user.user_id,
                bot_id=bot_id,
                exercises_get_in_session=user_bot_profile.exercises_get_in_session,
                exercises_get_in_set=user_bot_profile.exercises_get_in_set,
                last_exercise_at=now,
                last_long_break_reminder_type_sent=None,
                last_long_break_reminder_sent_at=None,
                current_streak_days=new_streak_days,
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
    ) -> Exercise:
        language_level = LanguageLevel.get_next_exercise_level(language_level)
        logger.debug(
            f'Next exercise level: {language_level} ' f'for user {user_id}'
        )
        exercise_type = ExerciseType.get_next_type()
        logger.debug(f'Next exercise type: {exercise_type} for user {user_id}')
        topic = ExerciseTopic.get_next_topic()
        logger.debug(f'Next exercise topic: {topic} for user {user_id}')

        exercise = await self.exercise_service.get_next_exercise(
            user_id=user_id,
            target_language=target_language,
            user_language=user_language,
            exercise_type=exercise_type,
            topic=topic,
            language_level=language_level,
        )

        if not exercise:
            logger.warning(f'No suitable exercise found for user {user_id}')
            raise ValueError(
                'No suitable exercise found for the provided criteria'
            )
        return exercise
