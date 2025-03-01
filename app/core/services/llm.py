from typing import Tuple

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.value_objects.answer import Answer


class LLMService:
    def generate_exercise(
        self, user: User, language_level: str, exercise_type: str
    ) -> Exercise:
        # TODO: Implement LLM interaction here
        raise NotImplementedError

    def validate_attempt(
        self, user: User, exercise: Exercise, attempt_data: Answer
    ) -> Tuple[bool, str]:
        # TODO: Implement LLM interaction here
        raise NotImplementedError
