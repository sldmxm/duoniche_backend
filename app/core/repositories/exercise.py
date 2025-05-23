from abc import ABC, abstractmethod
from typing import Optional

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel


class ExerciseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, exercise_id: int) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def create(self, exercise: Exercise) -> Exercise:
        raise NotImplementedError

    @abstractmethod
    async def get_new_exercise(
        self,
        user_id: int,
        target_language: str,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def get_any_new_exercise(
        self,
        user_id: int,
        target_language: str,
        exercise_type: Optional[ExerciseType],
    ) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def get_any_for_repetition(
        self,
        user_id: int,
        target_language: str,
    ) -> Optional[Exercise]:
        raise NotImplementedError

    @abstractmethod
    async def get_mistake_repetition(
        self,
        user_id: int,
        target_language: str,
    ) -> Optional[Exercise]:
        raise NotImplementedError
