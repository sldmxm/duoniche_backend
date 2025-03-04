from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.value_objects.answer import Answer


class LLMService:
    async def generate_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise:
        # Заглушка, в реальном приложении здесь будет вызов LLM
        raise NotImplementedError

    async def validate_attempt(
        self, user: User, exercise: Exercise, answer: Answer
    ) -> Tuple[bool, str]:
        # Заглушка, в реальном приложении здесь будет вызов LLM
        raise NotImplementedError
