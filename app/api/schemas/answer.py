from typing import List

from pydantic import BaseModel, Field


class AnswerSchema(BaseModel):
    type: str = Field(description='Type of answer')


class FillInTheBlankAnswerSchema(AnswerSchema):
    words: List[str] = Field(description='List of words')


class ChooseSentenceAnswerSchema(AnswerSchema):
    sentence: str = Field(description='Sentence')
