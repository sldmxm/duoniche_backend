from typing import Union

from pydantic import BaseModel, Field

from app.schemas.exercise_data import (
    FillInTheBlankExerciseDataSchema,
    MultipleChoiceExerciseDataSchema,
    SentenceConstructionExerciseDataSchema,
    TranslationExerciseDataSchema,
)


class ExerciseSchema(BaseModel):
    exercise_id: int = Field(description='Exercise ID')
    exercise_type: str = Field(description='Type of exercise')
    language_level: str = Field(description='Language level')
    topic: str = Field(description='Topic')
    exercise_text: str = Field(description='Exercise text')
    data: Union[
        SentenceConstructionExerciseDataSchema,
        MultipleChoiceExerciseDataSchema,
        FillInTheBlankExerciseDataSchema,
        TranslationExerciseDataSchema,
    ] = Field(description='Exercise data')
