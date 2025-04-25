from typing import Union

from pydantic import BaseModel, Field

from app.api.schemas.exercise_data import (
    ChooseExerciseDataSchema,
    FillInTheBlankExerciseDataSchema,
)


class ExerciseSchema(BaseModel):
    exercise_id: int = Field(description='Exercise ID')
    exercise_type: str = Field(description='Type of exercise')
    exercise_language: str = Field(description='Language of exercise')
    language_level: str = Field(description='Language level')
    topic: str = Field(description='Topic')
    exercise_text: str = Field(description='Exercise text')
    ui_template: str = Field(description='UI template')
    data: Union[
        FillInTheBlankExerciseDataSchema,
        ChooseExerciseDataSchema,
    ] = Field(description='Exercise data')
