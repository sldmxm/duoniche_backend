from typing import List

from pydantic import BaseModel, Field


class AnswerSchema(BaseModel):
    exercise_type: str = Field(description='Type of answer')


class FillInTheBlankAnswerSchema(AnswerSchema):
    words: List[str] = Field(description='List of words')


class ChooseAnswerSchema(AnswerSchema):
    answer: str = Field(description='Sentence')
