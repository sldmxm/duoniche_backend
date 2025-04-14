from abc import ABC, abstractmethod
from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.value_objects.answer import Answer


class ExerciseValidator(ABC):
    @abstractmethod
    async def validate(
        self,
        user_language: str,
        target_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        """Validate user's answer to the exercise."""
        pass
