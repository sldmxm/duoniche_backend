from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

from app.core.enums import ExerciseType
from app.core.value_objects.exercise import (
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    TranslationExerciseData,
)


class ExerciseDataSchema(BaseModel):
    type: str = Field(description='Type of exercise data')
    data: Dict[str, Any] = Field(description='Exercise data')

    @classmethod
    def from_exercise_data(
        cls,
        exercise_data: Union[
            FillInTheBlankExerciseData,
            MultipleChoiceExerciseData,
            SentenceConstructionExerciseData,
            TranslationExerciseData,
        ],
    ) -> Optional['ExerciseDataSchema']:
        # TODO: Переписать через генератор по словарю
        if isinstance(exercise_data, FillInTheBlankExerciseData):
            return cls(
                type='FillInTheBlankExerciseData',
                data=exercise_data.to_dict(),
            )
        elif isinstance(exercise_data, MultipleChoiceExerciseData):
            return cls(
                type='MultipleChoiceExerciseData',
                data=exercise_data.to_dict(),
            )
        elif isinstance(exercise_data, SentenceConstructionExerciseData):
            return cls(
                type='SentenceConstructionExerciseData',
                data=exercise_data.to_dict(),
            )
        elif isinstance(exercise_data, TranslationExerciseData):
            return cls(
                type='TranslationExerciseData',
                data=exercise_data.to_dict(),
            )
        else:
            raise ValueError(
                f'Unknown exercise data type: {type(exercise_data)}'
            )


class ExerciseSchema(BaseModel):
    exercise_id: int = Field(description='Exercise ID')
    exercise_type: ExerciseType = Field(description='Exercise type')
    language_level: str = Field(description='Language level')
    topic: str = Field(description='Exercise topic')
    exercise_text: str = Field(description='Exercise text')
    data: ExerciseDataSchema = Field(description='Exercise data')
