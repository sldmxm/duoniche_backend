from typing import Any, Dict

from app.core.entities.correct_answer import CorrectAnswer
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType as ExerciseTypeEnum
from app.core.interfaces.exercise_type import ExerciseType
from app.core.value_objects.answer import Answer
from app.core.value_objects.exercise import MultipleChoiceExerciseData


class MultipleChoiceExerciseType(ExerciseType):
    def validate_answer(
        self, exercise: Exercise, answer: Answer, correct_answer: CorrectAnswer
    ) -> bool:
        return (
            answer.get_answer_text() == correct_answer.answer.get_answer_text()
        )

    def generate_feedback(self, exercise: Exercise, answer: Answer) -> str:
        # TODO: Implement feedback generation
        return 'Try another option!'

    def get_exercise_type(self) -> str:
        return ExerciseTypeEnum.MULTIPLE_CHOICE.value

    def create_exercise(self, **kwargs: Dict[str, Any]) -> Exercise:
        language_level = str(kwargs.get('language_level', ''))
        if not language_level:
            raise ValueError('language_level is required')

        return Exercise(
            exercise_id=0,  # Will be set by repository
            exercise_type=self.get_exercise_type(),
            language_level=language_level,
            topic=str(kwargs.get('topic', 'grammar')),
            exercise_text=str(
                kwargs.get('exercise_text', 'Choose the correct answer')
            ),
            data=MultipleChoiceExerciseData(
                options=list(kwargs.get('options', []))
            ),
        )
