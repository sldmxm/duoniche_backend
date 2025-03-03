from app.core.enums import ExerciseType
from app.core.exercise_types.multiple_choice import MultipleChoiceExerciseType
from app.core.exercise_types.sentence_construction import (
    SentenceConstructionExerciseType,
)
from app.core.factories.exercise_factory import ExerciseFactory

# Register exercise types
ExerciseFactory.register_exercise_type(
    exercise_type=ExerciseType.SENTENCE_CONSTRUCTION.value,
    handler=SentenceConstructionExerciseType,
)
ExerciseFactory.register_exercise_type(
    exercise_type=ExerciseType.MULTIPLE_CHOICE.value,
    handler=MultipleChoiceExerciseType,
)
