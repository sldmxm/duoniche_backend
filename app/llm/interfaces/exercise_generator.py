from abc import ABC, abstractmethod
from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseTopic, LanguageLevel
from app.core.value_objects.answer import Answer
from app.llm.assessors.quality_assessor import ExerciseForAssessor


class ExerciseGenerator(ABC):
    @abstractmethod
    async def generate(
        self,
        user_language: str,
        user_language_code: str,
        target_language: str,
        language_level: LanguageLevel,
        topic: ExerciseTopic,
    ) -> Tuple[Exercise, Answer, ExerciseForAssessor]:
        """Generate an exercise for a user."""
        pass
