from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel, Field, model_validator

from app.core.configs.enums import (
    ExerciseStatus,
    ExerciseType,
    ExerciseUiTemplates,
    LanguageLevel,
)
from app.core.configs.exercise_templates import EXERCISE_UI_TEMPLATE_MAP
from app.core.configs.generation.config import ExerciseTopic
from app.core.value_objects.exercise import (
    ChooseAccentExerciseData,
    ChooseSentenceExerciseData,
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    StoryComprehensionExerciseData,
    TranslationExerciseData,
)

if TYPE_CHECKING:
    from app.core.entities.user_bot_profile import UserBotProfile


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
    persona: Optional[str] = Field(
        default=None, description='Persona of the exercise'
    )
    comments: Optional[str] = Field(
        default=None, description='Exercise comments'
    )
    grammar_tags: Optional[dict] = Field(
        default=None, description='Grammar and vocabulary tags.'
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

    def transliterate_to_cyrillic_if_needed(
        self, user_bot_profile: 'UserBotProfile'
    ) -> 'Exercise':
        """
        Returns a new Exercise instance transliterated to Cyrillic
        if the user's settings for Serbian require it.
        Otherwise, returns itself.
        """
        user_settings = user_bot_profile.settings
        if (
            user_settings
            and self.exercise_language == 'Serbian'
            and user_settings.alphabet == 'cyrillic'
        ):
            new_exercise = self.model_copy(deep=True)
            new_exercise.data = self.data.to_cyrillic()
            return new_exercise

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
