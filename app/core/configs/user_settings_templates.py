from app.core.configs.enums import ExerciseType
from app.core.entities.user_settings import UserSettings

FREE_PLAN_SETTINGS = UserSettings(
    available_exercise_types=[
        ExerciseType.FILL_IN_THE_BLANK,
        ExerciseType.CHOOSE_SENTENCE,
        ExerciseType.STORY_COMPREHENSION,
        ExerciseType.CHOOSE_ACCENT,
    ],
)

TRIAL_PLAN_SETTINGS = UserSettings(
    available_exercise_types=[ex_type for ex_type in ExerciseType],
    min_session_interval_minutes=0,
)

PREMIUM_PLAN_SETTINGS = UserSettings(
    available_exercise_types=[ex_type for ex_type in ExerciseType],
    min_session_interval_minutes=0,
)
