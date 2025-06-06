from abc import ABC, abstractmethod
from typing import Optional, Tuple

from app.core.entities.exercise import Exercise
from app.core.enums import LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.generation.persona import Persona
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
        persona: Optional[Persona] = None,
    ) -> Tuple[Exercise, Answer, ExerciseForAssessor]:
        """Generate an exercise for a user."""
        pass
