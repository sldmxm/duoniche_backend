from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ExerciseAttempt:
    attempt_id: int
    exercise_id: int
    user_id: int
    attempt_data: Dict[str, Any]
    is_correct: bool
    feedback: str | None = None
