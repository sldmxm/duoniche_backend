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
from app.core.enums import UserAction
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService
from app.core.texts import Messages, get_text

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
            # TODO:
            #  - переместить логику выбора следующего уровня, темы и типа
            #  - перенести из enum логику выбора уровня для пользователя
            exercise = await self.exercise_service.get_or_create_next_exercise(
                user
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
            return NextAction(
                action=UserAction.limit_reached,
                message=get_text(Messages.LIMIT_REACHED, user.user_language),
            )
        elif (
            user.session_frozen_until is not None
            or not user.session_started_at
        ):
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
