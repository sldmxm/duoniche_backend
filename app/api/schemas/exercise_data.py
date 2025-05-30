from typing import List

from pydantic import BaseModel, Field


class FillInTheBlankExerciseDataSchema(BaseModel):
    text_with_blanks: str = Field(description='Text with blanks')
    words: List[str] = Field(description='Words to fill in the blanks')


class ChooseExerciseDataSchema(BaseModel):
    options: List[str] = Field(description='List of sentences')


class AudioTextChooseExerciseDataSchema(BaseModel):
    content_text: str = Field(description='The content text')
    audio_url: str = Field(description='The audio url')
    audio_telegram_file_id: str = Field(
        description='The audio telegram file_id'
    )
    options: List[str] = Field(
        description='List of statements, one is correct'
    )
