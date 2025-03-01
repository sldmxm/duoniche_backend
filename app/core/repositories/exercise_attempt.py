from abc import ABC, abstractmethod
from typing import List

from app.core.entities.exercise_attempt import ExerciseAttempt


class ExerciseAttemptRepository(ABC):
    @abstractmethod
    def get_by_id(self, attempt_id: int) -> ExerciseAttempt | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_user_and_exercise(
        self, user_id: int, exercise_id: int
    ) -> List[ExerciseAttempt] | None:
        raise NotImplementedError

    @abstractmethod
    def get_all_user_attempts(
        self, user_id: int
    ) -> List[ExerciseAttempt] | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, exercise_attempt: ExerciseAttempt) -> ExerciseAttempt:
        raise NotImplementedError
