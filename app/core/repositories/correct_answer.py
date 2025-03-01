from abc import ABC, abstractmethod
from typing import List

from app.core.entities.correct_answer import CorrectAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt


class CorrectAnswerRepository(ABC):
    @abstractmethod
    def get_by_id(self, correct_answer_id: int) -> CorrectAnswer | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[CorrectAnswer] | None:
        raise NotImplementedError

    @abstractmethod
    def save(self, correct_answer: CorrectAnswer) -> CorrectAnswer:
        raise NotImplementedError

    @abstractmethod
    def get_attempts(
        self, correct_answer_id: int
    ) -> List[ExerciseAttempt] | None:
        raise NotImplementedError
