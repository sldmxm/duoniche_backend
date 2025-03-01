from dataclasses import dataclass
from datetime import datetime

from app.core.value_objects.answer import Answer


@dataclass
class CorrectAnswer:
    correct_answer_id: int
    exercise_id: int
    answer: Answer
    created_at: datetime | None = None
    created_by: str | None = None
