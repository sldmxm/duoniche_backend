from dataclasses import dataclass
from datetime import datetime

from app.core.value_objects.answer import Answer


@dataclass
class CachedAnswer:
    answer_id: int
    exercise_id: int
    answer: Answer
    is_correct: bool
    feedback: str
    created_at: datetime
    created_by: str
