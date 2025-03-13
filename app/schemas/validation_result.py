from typing import Optional

from pydantic import BaseModel, Field


class ValidationResultSchema(BaseModel):
    is_correct: bool = Field(description='Whether the answer is correct')
    feedback: Optional[str] = Field(description='Feedback on the answer')
