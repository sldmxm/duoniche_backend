from dataclasses import dataclass
from typing import Any, Dict, Union

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
    # TODO: Добавить на всех слоях язык упражнения
    language_level: str
    topic: str
    # TODO: Заполнять тест задания в зависимости
    #  от типа задания и языка пользовтеля
    exercise_text: str
    data: Union[
        SentenceConstructionExerciseData,
        MultipleChoiceExerciseData,
        FillInTheBlankExerciseData,
        TranslationExerciseData,
    ]

    def model_dump(self):
        return {
            'exercise_id': self.exercise_id,
            'exercise_type': self.exercise_type,
            'language_level': self.language_level,
            'topic': self.topic,
            'exercise_text': self.exercise_text,
            'data': self.data.to_dict(),
        }

    @classmethod
    def get_data_from_dict(cls, data: Dict[str, Any]):
        exercise_types = {
            'SentenceConstructionExerciseData': (
                SentenceConstructionExerciseData
            ),
            'MultipleChoiceExerciseData': MultipleChoiceExerciseData,
            'FillInTheBlankExerciseData': FillInTheBlankExerciseData,
            'TranslationExerciseData': TranslationExerciseData,
        }
        exercise_type = exercise_types.get(data['type'])
        if not exercise_type:
            raise ValueError(f'Unknown exercise type: {exercise_type}')
        return exercise_type(**data['data'])
