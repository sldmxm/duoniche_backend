from abc import ABC, abstractmethod
from typing import List, Optional

from app.core.entities.exercise_attempt import ExerciseAttempt


class ExerciseAttemptRepository(ABC):
    @abstractmethod
    async def get_by_id(self, attempt_id: int) -> Optional[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def get_all(self) -> List[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_exercise(
        self, user_id: int, exercise_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_id(
        self, user_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_exercise_id(
        self, exercise_id: int
    ) -> List[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def create(
        self, exercise_attempt: ExerciseAttempt
    ) -> ExerciseAttempt:
        raise NotImplementedError

    @abstractmethod
    async def update(
        self,
        attempt_id: int,
        is_correct: bool,
        feedback: Optional[str],
        answer_id: int,
    ) -> ExerciseAttempt:
        raise NotImplementedError
