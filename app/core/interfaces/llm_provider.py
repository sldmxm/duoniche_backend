from abc import ABC, abstractmethod
from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseTopic, ExerciseType, LanguageLevel
from app.core.value_objects.answer import Answer


class LLMProvider(ABC):
    @abstractmethod
    async def generate_exercise(
        self,
        user: User,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> tuple[Exercise, Answer]:
        pass

    @abstractmethod
    async def validate_attempt(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        pass
