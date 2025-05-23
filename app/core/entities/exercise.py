from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.core.enums import (
    ExerciseTopic,
    ExerciseType,
    ExerciseUiTemplates,
    LanguageLevel,
)
from app.core.exercise_templates import EXERCISE_UI_TEMPLATE_MAP
from app.core.value_objects.exercise import (
    ChooseAccentExerciseData,
    ChooseSentenceExerciseData,
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    TranslationExerciseData,
    create_exercise_data_model_validate,
)


class Exercise(BaseModel):
    exercise_id: Optional[int] = Field(description='Exercise ID')
    exercise_type: ExerciseType = Field(description='Type of exercise')
    exercise_language: str = Field(description='Language of exercise')
    language_level: LanguageLevel = Field(description='Language level')
    topic: ExerciseTopic = Field(description='Topic')
    exercise_text: str = Field(description='Exercise text')
    ui_template: Optional[ExerciseUiTemplates] = None

    data: Union[
        FillInTheBlankExerciseData,
        ChooseSentenceExerciseData,
        ChooseAccentExerciseData,
        SentenceConstructionExerciseData,
        MultipleChoiceExerciseData,
        TranslationExerciseData,
    ] = Field(description='Exercise data')

    @model_validator(mode='after')
    def assign_ui_template(self) -> 'Exercise':
        self.ui_template = EXERCISE_UI_TEMPLATE_MAP[self.exercise_type]
        return self

    # TODO: Сделать такое же в Answer и поменять в модулях
    @classmethod
    def get_data_model_validate(cls, data: Dict[str, Any]):
        return create_exercise_data_model_validate(data)

    def __str__(self):
        return (
            f'Exercise(exercise_id={self.exercise_id}, '
            f'exercise_type={self.exercise_type}, '
            f'exercise_language={self.exercise_language}, '
            f'language_level={self.language_level}, '
            f'topic={self.topic}, '
            f'exercise_text={self.exercise_text}, '
            f'data={self.data})'
        )
