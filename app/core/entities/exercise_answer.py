from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.value_objects.answer import Answer


class ExerciseAnswer(BaseModel):
    answer_id: Optional[int] = Field()
    exercise_id: int = Field()
    answer: Answer = Field()
    is_correct: bool = Field()
    feedback: str = Field()
    feedback_language: str = Field()
    error_tags: Optional[dict] = Field(
        default=None, description='Categorized error tags.'
    )
    created_at: datetime = Field()
    created_by: str = Field()
