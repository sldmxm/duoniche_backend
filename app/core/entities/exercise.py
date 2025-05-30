from typing import Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.core.enums import (
    ExerciseStatus,
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
    StoryComprehensionExerciseData,
    TranslationExerciseData,
)


class Exercise(BaseModel):
    exercise_id: Optional[int] = Field(None, description='Exercise ID')
    exercise_type: ExerciseType = Field(description='Type of exercise')
    exercise_language: str = Field(description='Language of exercise')
    language_level: LanguageLevel = Field(description='Language level')
    topic: ExerciseTopic = Field(description='Topic')
    exercise_text: str = Field(description='Exercise text')
    ui_template: Optional[ExerciseUiTemplates] = None
    status: ExerciseStatus = Field(
        default=ExerciseStatus.PUBLISHED, description='Status of the exercise'
    )

    data: Union[
        FillInTheBlankExerciseData,
        ChooseSentenceExerciseData,
        ChooseAccentExerciseData,
        StoryComprehensionExerciseData,
        SentenceConstructionExerciseData,
        MultipleChoiceExerciseData,
        TranslationExerciseData,
    ] = Field(description='Exercise data', discriminator='type')

    @model_validator(mode='after')
    def assign_ui_template(self) -> 'Exercise':
        self.ui_template = EXERCISE_UI_TEMPLATE_MAP[self.exercise_type]
        return self

    def __str__(self):
        return (
            f'Exercise(exercise_id={self.exercise_id}, '
            f'exercise_type={self.exercise_type.value}, '
            f'status={self.status.value}, '
            f'exercise_language={self.exercise_language}, '
            f'language_level={self.language_level.value}, '
            f'topic={self.topic.value}, '
            f'exercise_text={self.exercise_text}, '
            f'data={self.data})'
        )
