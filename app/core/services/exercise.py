from app.core.entities.correct_answer import CorrectAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.factories.exercise_factory import ExerciseFactory
from app.core.repositories.correct_answer import CorrectAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.llm import LLMService
from app.core.value_objects.answer import Answer


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        correct_answer_repository: CorrectAnswerRepository,
        llm_service: LLMService,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.correct_answer_repository = correct_answer_repository
        self.llm_service = llm_service

    def get_new_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise | None:
        exercise = self.exercise_repository.get_new_exercise(
            user, language_level, exercise_type
        )
        if not exercise:
            exercise = self.llm_service.generate_exercise(
                user, language_level, exercise_type
            )
            self.save_exercise(exercise)

        return exercise

    def get_exercise_for_repetition(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise | None:
        exercise = self.exercise_repository.get_exercise_for_repetition(
            user, language_level, exercise_type
        )
        if not exercise:
            return None
        return exercise

    def get_exercise_by_id(self, exercise_id: int) -> Exercise | None:
        return self.exercise_repository.get_by_id(exercise_id)

    def save_exercise(self, exercise: Exercise) -> Exercise:
        return self.exercise_repository.save(exercise)

    def validate_exercise_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> ExerciseAttempt:
        # Получаем обработчик для типа упражнения
        exercise_handler = ExerciseFactory.get_handler(exercise.exercise_type)

        # Проверяем ответ через кэш правильных ответов
        is_correct = False
        feedback = None
        correct_answer_obj = None

        # Проверяем через кэш
        correct_answers = self.correct_answer_repository.get_by_exercise_id(
            exercise.exercise_id
        )

        if correct_answers:
            for correct_answer in correct_answers:
                if exercise_handler.validate_answer(
                    exercise, answer, correct_answer
                ):
                    is_correct = True
                    correct_answer_obj = correct_answer
                    break

        # Если ответ не найден в кэше, проверяем через LLM
        if not is_correct:
            is_correct, feedback = self.llm_service.validate_attempt(
                user, exercise, answer
            )

        # Создаем попытку
        exercise_attempt = ExerciseAttempt(
            attempt_id=0,
            user_id=user.user_id,
            exercise_id=exercise.exercise_id,
            answer=answer,
            is_correct=is_correct,
            feedback=feedback or ('Correct!' if is_correct else 'Wrong!'),
        )

        # Сохраняем правильный ответ в кэш
        if is_correct and not correct_answer_obj:
            self.add_correct_answer(
                exercise=exercise,
                answer=answer,
                created_by=f'LLM:user:{user.user_id}',
            )

        return self.save_exercise_attempt(exercise_attempt)

    def save_exercise_attempt(
        self, exercise_attempt: ExerciseAttempt
    ) -> ExerciseAttempt:
        return self.exercise_attempt_repository.save(exercise_attempt)

    def add_correct_answer(
        self, exercise: Exercise, answer: Answer, created_by: str
    ) -> CorrectAnswer:
        correct_answer = CorrectAnswer(
            correct_answer_id=0,
            exercise_id=exercise.exercise_id,
            answer=answer,
            created_by=created_by,
        )
        return self.correct_answer_repository.save(correct_answer)
