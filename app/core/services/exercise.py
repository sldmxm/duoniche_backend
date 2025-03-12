from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.interfaces.llm_provider import LLMProvider
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.value_objects.answer import Answer


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        cached_answer_repository: CachedAnswerRepository,
        llm_service: LLMProvider,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.cached_answer_repository = cached_answer_repository
        self.llm_service = llm_service

    async def get_new_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise | None:
        exercise = await self.exercise_repository.get_new_exercise(
            user, language_level, exercise_type
        )
        if not exercise:
            exercise = await self.llm_service.generate_exercise(
                user, language_level, exercise_type
            )
            await self.save_exercise(exercise)

        return exercise

    async def get_exercise_for_repetition(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise | None:
        return await self.exercise_repository.get_exercise_for_repetition(
            user, language_level, exercise_type
        )

    async def get_exercise_by_id(self, exercise_id: int) -> Exercise | None:
        return await self.exercise_repository.get_by_id(exercise_id)

    async def save_exercise(self, exercise: Exercise) -> Exercise:
        return await self.exercise_repository.save(exercise)

    async def validate_exercise_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAttempt:
        cached_answer = (
            await self.cached_answer_repository.get_by_exercise_and_answer(
                exercise.exercise_id, answer
            )
        )
        if not cached_answer:
            is_correct, feedback = await self.llm_service.validate_attempt(
                user, exercise, answer
            )
            cached_answer = CachedAnswer(
                answer_id=0,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=is_correct,
                feedback=feedback,
                # TODO: Вынести в константу
                #  ИЛИ добавить атрибуты в модель, чтобы понимать,
                #  как принято решение о правильности ответа
                created_by=f'LLM:user:{user.user_id}',
            )

            cached_answer = await self.cached_answer_repository.save(
                cached_answer
            )

        return await self.save_exercise_attempt(
            ExerciseAttempt(
                attempt_id=0,
                user_id=user.user_id,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=cached_answer.is_correct,
                feedback=cached_answer.feedback,
                cached_answer_id=cached_answer.answer_id,
            )
        )

    async def save_exercise_attempt(
        self, exercise_attempt: ExerciseAttempt
    ) -> ExerciseAttempt:
        return await self.exercise_attempt_repository.save(exercise_attempt)

    async def _check_cached_answer(
        self, exercise_id: int, answer: Answer
    ) -> CachedAnswer | None:
        return await self.cached_answer_repository.get_by_exercise_and_answer(
            exercise_id, answer
        )

    async def _create_cached_answer(
        self, exercise_id: int, answer: Answer
    ) -> CachedAnswer:
        # В реальном приложении здесь будет логика проверки ответа
        # Сейчас просто заглушка
        cached_answer = await self.cached_answer_repository.save(
            CachedAnswer(
                answer_id=0,
                exercise_id=exercise_id,
                answer=answer,
                is_correct=True,  # Заглушка
                feedback='Good job!',  # Заглушка
                created_at=None,  # Будет установлено в БД
                created_by=None,  # Будет установлено позже
            )
        )
        return cached_answer

    async def check_answer(
        self,
        user_id: int,
        exercise_id: int,
        answer: Answer,
    ) -> ExerciseAttempt:
        # Проверяем, есть ли такой ответ в кэше
        # TODO: надо еще проверять язык пользователя,
        #  если ответ неправильный и нужен перевод комментария LLM
        cached_answer = await self._check_cached_answer(exercise_id, answer)

        if not cached_answer:
            # Если ответа нет в кэше, создаем новый
            cached_answer = await self._create_cached_answer(
                exercise_id, answer
            )

        # Создаем попытку
        attempt = await self.exercise_attempt_repository.save(
            ExerciseAttempt(
                attempt_id=0,
                user_id=user_id,
                exercise_id=exercise_id,
                answer=answer,
                is_correct=cached_answer.is_correct,
                feedback=cached_answer.feedback,
                cached_answer_id=cached_answer.answer_id,
            )
        )

        return attempt
