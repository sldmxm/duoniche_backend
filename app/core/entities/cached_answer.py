from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.core.value_objects.answer import Answer, FillInTheBlankAnswer


class CachedAnswer(BaseModel):
    answer_id: Optional[int] = Field()
    exercise_id: int = Field()
    answer: Answer = Field()
    is_correct: bool = Field()
    feedback: str = Field()
    created_at: datetime = Field()
    created_by: str = Field()

    def model_dump(self):
        return {
            'answer_id': self.answer_id,
            'exercise_id': self.exercise_id,
            'answer': self.answer.to_dict(),
            'is_correct': self.is_correct,
            'feedback': self.feedback,
            'created_at': self.created_at,
            'created_by': self.created_by,
        }

    @classmethod
    def get_answer_from_dict(cls, data: dict):
        if data['type'] == 'fill_in_the_blank':
            return FillInTheBlankAnswer(**data)
        else:
            raise ValueError(f'Unknown answer type: {data["type"]}')
