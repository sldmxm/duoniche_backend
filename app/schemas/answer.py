from typing import List

from pydantic import BaseModel, Field


class FillInTheBlankAnswerSchema(BaseModel):
    words: List[str] = Field(description='List of words')
