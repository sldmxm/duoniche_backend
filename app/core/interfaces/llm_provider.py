from abc import ABC, abstractmethod
from typing import List, Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.value_objects.answer import Answer


class LLMProvider(ABC):
    @abstractmethod
    async def generate_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> tuple[Exercise, Answer]:
        pass

    @abstractmethod
    async def validate_attempt(
        self,
        user: User,
        exercise: Exercise,
        answer: Answer,
        right_answer: List[Answer],
    ) -> Tuple[bool, str]:
        pass
