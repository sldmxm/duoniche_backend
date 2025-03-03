from typing import Any, Dict

from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType as ExerciseTypeEnum
from app.core.interfaces.exercise_type import ExerciseType
from app.core.value_objects.answer import Answer
from app.core.value_objects.exercise import SentenceConstructionExerciseData


class SentenceConstructionExerciseType(ExerciseType):
    def generate_feedback(self, exercise: Exercise, answer: Answer) -> str:
        # TODO: Implement feedback generation
        return 'Keep trying!'

    def get_exercise_type(self) -> str:
        return ExerciseTypeEnum.SENTENCE_CONSTRUCTION.value

    def create_exercise(self, **kwargs: Dict[str, Any]) -> Exercise:
        language_level = str(kwargs.get('language_level', ''))
        if not language_level:
            raise ValueError('language_level is required')

        return Exercise(
            exercise_id=0,  # Will be set by repository
            exercise_type=self.get_exercise_type(),
            language_level=language_level,
            topic=str(kwargs.get('topic', 'general')),
            exercise_text=str(kwargs.get('exercise_text', 'Make a sentence')),
            data=SentenceConstructionExerciseData(
                words=list(kwargs.get('words', []))
            ),
        )
