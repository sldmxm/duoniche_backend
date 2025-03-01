from dataclasses import dataclass
from typing import Union

from app.core.value_objects.exercise import (
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    TranslationExerciseData,
)


@dataclass
class Exercise:
    exercise_id: int
    exercise_type: str
    language_level: str
    topic: str
    exercise_text: str
    data: Union[
        SentenceConstructionExerciseData,
        MultipleChoiceExerciseData,
        FillInTheBlankExerciseData,
        TranslationExerciseData,
    ]
