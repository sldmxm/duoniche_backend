from abc import ABC, abstractmethod

from app.core.entities.exercise import Exercise
from app.core.entities.user import User


class ExerciseRepository(ABC):
    @abstractmethod
    def get_by_id(self, exercise_id: int) -> Exercise | None:
        raise NotImplementedError

    @abstractmethod
    def get_new_exercise(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Exercise | None:
        raise NotImplementedError

    @abstractmethod
    def get_exercise_for_repetition(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Exercise | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, exercise: Exercise) -> Exercise:
        raise NotImplementedError
