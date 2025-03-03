from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.entities.cached_answer import CachedAnswer
from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.value_objects.answer import Answer


class CachedAnswerRepository(ABC):
    @abstractmethod
    def get_by_id(self, answer_id: int) -> Optional[CachedAnswer]:
        raise NotImplementedError

    @abstractmethod
    def get_by_exercise_id(self, exercise_id: int) -> List[CachedAnswer]:
        raise NotImplementedError

    @abstractmethod
    def save(self, cached_answer: CachedAnswer) -> CachedAnswer:
        raise NotImplementedError

    @abstractmethod
    def get_attempts(self, answer_id: int) -> List[ExerciseAttempt] | None:
        raise NotImplementedError

    @abstractmethod
    def get_by_exercise_and_answer(
        self, exercise_id: int, answer: Answer
    ) -> CachedAnswer | None:
        raise NotImplementedError
