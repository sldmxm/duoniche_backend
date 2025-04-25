from typing import List

from pydantic import BaseModel, Field


class FillInTheBlankExerciseDataSchema(BaseModel):
    text_with_blanks: str = Field(description='Text with blanks')
    words: List[str] = Field(description='Words to fill in the blanks')


class ChooseExerciseDataSchema(BaseModel):
    options: List[str] = Field(description='List of sentences')
