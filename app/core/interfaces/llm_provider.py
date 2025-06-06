from abc import ABC, abstractmethod
from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType, LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.value_objects.answer import Answer


class LLMProvider(ABC):
    @abstractmethod
    async def generate_exercise(
        self,
        user_language: str,
        target_language: str,
        language_level: LanguageLevel,
        exercise_type: ExerciseType,
        topic: ExerciseTopic,
    ) -> tuple[Exercise, Answer]:
        pass

    @abstractmethod
    async def validate_attempt(
        self,
        user_language: str,
        exercise: Exercise,
        answer: Answer,
    ) -> Tuple[bool, str]:
        pass
