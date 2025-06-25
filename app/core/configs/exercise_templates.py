from app.core.configs.enums import ExerciseType, ExerciseUiTemplates

EXERCISE_UI_TEMPLATE_MAP = {
    ExerciseType.FILL_IN_THE_BLANK: ExerciseUiTemplates.FILL_IN_THE_BLANK,
    ExerciseType.CHOOSE_SENTENCE: ExerciseUiTemplates.CHOOSE,
    ExerciseType.CHOOSE_ACCENT: ExerciseUiTemplates.CHOOSE,
    ExerciseType.STORY_COMPREHENSION: ExerciseUiTemplates.AUDIO_CHOOSE,
}
