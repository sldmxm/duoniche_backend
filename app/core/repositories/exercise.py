from abc import abstractmethod
from typing import Optional

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.repositories.base import AsyncRepository


class ExerciseRepository(AsyncRepository[Exercise]):
    @abstractmethod
    async def get_by_id(self, exercise_id: int) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def get_new_exercise(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def get_exercise_for_repetition(
        self,
        user: User,
        language_level: str,
        exercise_type: str,
    ) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def save(self, exercise: Exercise) -> Exercise:
        raise NotImplementedError
