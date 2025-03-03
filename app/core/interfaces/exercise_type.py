from abc import ABC, abstractmethod
from typing import Any, Dict

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer


class ExerciseType(ABC):
    @abstractmethod
    def validate_answer(
        self, exercise: Exercise, answer: Answer, correct_answer: Any
    ) -> bool:
        pass

    @abstractmethod
    def generate_feedback(self, exercise: Exercise, answer: Answer) -> str:
        pass

    @abstractmethod
    def get_exercise_type(self) -> str:
        pass

    @abstractmethod
    def create_exercise(self, **kwargs: Dict[str, Any]) -> Exercise:
        pass
