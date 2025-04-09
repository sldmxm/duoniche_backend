from abc import ABC, abstractmethod
from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, LanguageLevel
from app.core.value_objects.answer import Answer


class ExerciseGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        user: User,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
    ) -> Tuple[Exercise, Answer]:
        """Generate an exercise for a user."""
        pass
