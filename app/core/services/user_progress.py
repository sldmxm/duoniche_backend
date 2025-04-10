import logging
from datetime import datetime, timezone

from app.core.consts import (
    DELTA_BETWEEN_SESSIONS,
    EXERCISES_IN_SET,
    RENEWING_SET_PERIOD,
    SETS_IN_SESSION,
)
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.enums import (
    ExerciseTopic,
    ExerciseType,
    LanguageLevel,
    UserAction,
)
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.texts import Messages, get_text
from app.metrics import BACKEND_EXERCISE_METRICS, BACKEND_USER_METRICS

logger = logging.getLogger(__name__)


class UserProgressService:
    def __init__(
        self,
        user_service: UserService,
        exercise_service: ExerciseService,
    ):
        self.user_service = user_service
        self.exercise_service = exercise_service

    async def get_next_action(self, user_id: int) -> NextAction:
        async def _get_next_exercise(user: User) -> Exercise:
            language_level = LanguageLevel.get_next_exercise_level(
                user.language_level
            )
            logger.debug(
                f'Next exercise level: {language_level} for user {user}'
            )
            exercise_type = ExerciseType.get_next_type()
            topic = ExerciseTopic.get_next_topic()
            logger.debug(f'Next exercise topic: {topic} for user {user}')
            exercise = await self.exercise_service.get_or_create_next_exercise(
                user=user,
                exercise_type=exercise_type,
                topic=topic,
                language_level=language_level,
            )
            if not exercise:
                raise ValueError(
                    'No suitable exercise found for the provided criteria'
                )
            return exercise

        # TODO: разобраться, как собирать количество ошибок,
        #  возможно, просто в верификации брать и писать в бд пользователя
        #  ИЛИ !!! вообще убрать эти дополнительные поля у пользователя
        #  и брать все из БД ответов, а у пользователя сохранять
        #  id первого упражнения в сессии

        user = await self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError('User with provided ID not found in the database')

        now = datetime.now(timezone.utc)

        if (
            user.session_frozen_until is not None
            and now < user.session_frozen_until
        ):
            logger.debug(
                f'User {user.user_id} is frozen until '
                f'{user.session_frozen_until}, {now=}'
            )
            BACKEND_USER_METRICS['frozen_attempts'].labels(
                cohort=user.cohort,
                plan=user.plan,
                target_language=user.target_language,
                user_language=user.user_language,
                language_level=user.language_level.value,
            ).inc()

            return NextAction(
                action=UserAction.limit_reached,
                message=get_text(Messages.LIMIT_REACHED, user.user_language),
            )
        elif (
            # was frozen, but now unfrozen
            user.session_frozen_until is not None
            # new user
            or not user.session_started_at
        ):
            if user.session_frozen_until is not None:
                logger.debug(
                    f'User {user.user_id} WAS frozen '
                    f'until {user.session_frozen_until}, {now=}'
                )

            user.session_frozen_until = None
            user.session_started_at = now
            user.exercises_get_in_session = 0
            user.exercises_get_in_set = 0
            await self.user_service.update(user)

        current_session_time = now - user.session_started_at
        renewed_sets = int(
            current_session_time.total_seconds()
            // RENEWING_SET_PERIOD.total_seconds()
        )
        current_set_limit = max(SETS_IN_SESSION, renewed_sets)
        current_exercises_limit = current_set_limit * EXERCISES_IN_SET

        if current_exercises_limit - user.exercises_get_in_session <= 0:
            user.session_frozen_until = now + DELTA_BETWEEN_SESSIONS
            await self.user_service.update(user)

            return NextAction(
                action=UserAction.congratulations_and_wait,
                message=get_text(
                    Messages.CONGRATULATIONS_AND_WAIT,
                    user.user_language,
                    exercise_num=user.exercises_get_in_session,
                ),
                pause=DELTA_BETWEEN_SESSIONS,
            )

        if user.exercises_get_in_set < EXERCISES_IN_SET:
            try:
                next_exercise = await _get_next_exercise(user)

                user.exercises_get_in_session += 1
                user.exercises_get_in_set += 1
                user.last_exercise_at = now
                await self.user_service.update(user)

                BACKEND_EXERCISE_METRICS['sent'].labels(
                    exercise_type=next_exercise.exercise_type.value,
                    level=next_exercise.language_level.value,
                ).inc()

                return NextAction(
                    exercise=next_exercise,
                    action=UserAction.new_exercise,
                )
            except ValueError:
                return NextAction(
                    action=UserAction.error,
                    message=get_text(
                        Messages.ERROR_GETTING_NEW_EXERCISE, user.user_language
                    ),
                )
        else:
            user.exercises_get_in_set = 0
            user.errors_count_in_set = 0
            await self.user_service.update(user)

            return NextAction(
                action=UserAction.praise_and_next_set,
                message=get_text(
                    Messages.PRAISE_AND_NEXT_SET, user.user_language
                ),
            )
