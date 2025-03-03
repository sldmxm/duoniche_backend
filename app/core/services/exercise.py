from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise import Exercise
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.entities.user import User
from app.core.repositories.cached_answer import CachedAnswerRepository
from app.core.repositories.exercise import ExerciseRepository
from app.core.repositories.exercise_attempt import ExerciseAttemptRepository
from app.core.services.llm import LLMService
from app.core.value_objects.answer import Answer


class ExerciseService:
    def __init__(
        self,
        exercise_repository: ExerciseRepository,
        exercise_attempt_repository: ExerciseAttemptRepository,
        cached_answer_repository: CachedAnswerRepository,
        llm_service: LLMService,
    ):
        self.exercise_repository = exercise_repository
        self.exercise_attempt_repository = exercise_attempt_repository
        self.cached_answer_repository = cached_answer_repository
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
        cached_answer = (
            self.cached_answer_repository.get_by_exercise_and_answer(
                exercise.exercise_id, answer
            )
        )
        if not cached_answer:
            is_correct, feedback = self.llm_service.validate_attempt(
                user, exercise, answer
            )
            cached_answer = CachedAnswer(
                answer_id=0,
                exercise_id=exercise.exercise_id,
                answer=answer,
                is_correct=is_correct,
                feedback=feedback,
                created_by=f'LLM:user:{user.user_id}',
            )

            cached_answer = self.cached_answer_repository.save(cached_answer)

        return self.save_exercise_attempt(
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

    def save_exercise_attempt(
        self, exercise_attempt: ExerciseAttempt
    ) -> ExerciseAttempt:
        return self.exercise_attempt_repository.save(exercise_attempt)
