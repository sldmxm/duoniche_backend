from abc import abstractmethod
from typing import List, Optional

from app.core.entities.exercise_attempt import ExerciseAttempt
from app.core.repositories.base import AsyncRepository


class ExerciseAttemptRepository(AsyncRepository[ExerciseAttempt]):
    @abstractmethod
    async def get_by_id(self, attempt_id: int) -> Optional[ExerciseAttempt]:
        raise NotImplementedError

    @abstractmethod
    async def get_by_user_and_exercise(
        self, user_id: int, exercise_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def get_all_user_attempts(
        self, user_id: int
    ) -> Optional[List[ExerciseAttempt]]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, exercise_attempt: ExerciseAttempt) -> ExerciseAttempt:
        raise NotImplementedError
