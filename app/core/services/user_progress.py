import logging
from datetime import datetime, timezone

from app.core.consts import (
    DELTA_BETWEEN_SESSIONS,
    EXERCISES_IN_SESSION,
    EXERCISES_IN_SET,
)
from app.core.entities.exercise import Exercise
from app.core.entities.next_action_result import NextAction
from app.core.entities.user import User
from app.core.enums import UserAction
from app.core.services.exercise import ExerciseService
from app.core.services.user import UserService

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
        """
        Determine the next action for the user based on their progress.
        """

        async def _next_exercise(user: User) -> Exercise:
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

        # TODO: ровно в момент окончания паузы бот
        #  должен отправить запрос на API

        # TODO: разобраться, как собирать количество ошибок,
        #  возможно, просто в верификации брать и писать в бд пользователя
        #  ИЛИ !!! вообще убрать эти дополнительные поля у пользователя
        #  и брать все из БД ответов, а у пользователя сохранять
        #  id первого упражнения в сессии

        user = await self.user_service.get_by_id(user_id)
        if not user:
            raise ValueError('User with provided ID not found in the database')

        now = datetime.now(timezone.utc)
        if user.is_waiting_next_session:
            if (
                user.last_exercise_at
                and user.last_exercise_at + DELTA_BETWEEN_SESSIONS > now
            ):
                return NextAction(
                    action=UserAction.limit_reached,
                    # TODO: Писать на болгарском или языке пользователя,
                    #  сделать словарь фиксированных сообщений
                    message="I'll send you new exercise ASAP...",
                )
            else:
                user.is_waiting_next_session = False

        if user.exercises_get_in_session < EXERCISES_IN_SESSION:
            if user.exercises_get_in_set < EXERCISES_IN_SET:
                next_exercise = await _next_exercise(user)

                user.exercises_get_in_session += 1
                user.exercises_get_in_set += 1
                user.last_exercise_at = now
                await self.user_service.update(user)

                return NextAction(
                    exercise=next_exercise,
                    action=UserAction.new_exercise,
                )
            else:
                # TODO: Разные сообщения для разного количества ошибок
                #  найти за что хвалить, например,
                #  за короткое или длинное время сета
                message = (
                    'You are doing great!\n '
                    f'You have {user.errors_count_in_set} '
                    f'errors in previous set!'
                )

                user.exercises_get_in_set = 0
                user.errors_count_in_set = 0
                await self.user_service.update(user)

                return NextAction(
                    action=UserAction.praise_and_next_set,
                    message=message,
                )
        else:
            user.is_waiting_next_session = True
            user.exercises_get_in_session = 0
            user.exercises_get_in_set = 0
            await self.user_service.update(user)
            # TODO:
            #  - Разные сообщения для разного количества ошибок
            #  найти за что хвалить, например,
            #   за короткое или длинное время сессии
            #  - Второе сообщение отдельно в боте
            #   "подожди или плоти", разделить \n
            message = (
                f'Wow! {EXERCISES_IN_SESSION} in row!\n'
                f'Wait for NNN hours!!!!!!'
            )

            return NextAction(
                action=UserAction.congratulations_and_wait,
                message=message,
                pause=DELTA_BETWEEN_SESSIONS,
            )
