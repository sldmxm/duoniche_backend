from typing import Optional

from pydantic import BaseModel, Field

from app.core.value_objects.answer import Answer


class ExerciseAttempt(BaseModel):
    attempt_id: Optional[int] = Field()
    exercise_id: int = Field()
    user_id: Optional[int] = Field()
    answer: Answer = Field()
    is_correct: Optional[bool] = Field()
    feedback: Optional[str] = Field()
    answer_id: Optional[int] = Field()
    error_tags: Optional[dict] = Field(
        default=None, description='Categorized error tags.'
    )
