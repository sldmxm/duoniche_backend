from typing import List

from pydantic import BaseModel, Field


class FillInTheBlankExerciseDataSchema(BaseModel):
    text_with_blanks: str = Field(description='Text with blanks')
    words: List[str] = Field(description='Words to fill in the blanks')


class ChooseSentenceExerciseDataSchema(BaseModel):
    sentences: List[str] = Field(description='List of sentences')


class ChooseAccentExerciseDataSchema(BaseModel):
    accents: List[str] = Field(description='List of accents')


class MultipleChoiceExerciseDataSchema(BaseModel):
    question: str = Field(description='Question')
    options: List[str] = Field(description='Options')
    correct_answer: str = Field(description='Correct answer')


class SentenceConstructionExerciseDataSchema(BaseModel):
    words: List[str] = Field(description='Words to construct a sentence')


class TranslationExerciseDataSchema(BaseModel):
    text: str = Field(description='Text to translate')
