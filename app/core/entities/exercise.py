from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

from app.core.value_objects.exercise import (
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    TranslationExerciseData,
)


class Exercise(BaseModel):
    exercise_id: Optional[int] = Field(description='Exercise ID')
    exercise_type: str = Field(description='Type of exercise')
    # TODO: Вынести уровень в ENUM в формате A1-C2
    language_level: str = Field(description='Language level')
    topic: str = Field(description='Topic')
    # TODO: Заполнять тест задания в зависимости
    #  от типа задания и языка пользователя
    exercise_text: str = Field(description='Exercise text')
    # TODO: Добавить на всех слоях язык упражнения,
    #  в том числе, при выборке в БД
    # TODO: Добавить на всех слоях created_at и created_by
    data: Union[
        SentenceConstructionExerciseData,
        MultipleChoiceExerciseData,
        FillInTheBlankExerciseData,
        TranslationExerciseData,
    ] = Field(description='Exercise data')

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
            raise ValueError(f"Unknown exercise type: {data['type']}")
        return exercise_type(**data)

    def __str__(self):
        return (
            f'Exercise(exercise_id={self.exercise_id}, '
            f'exercise_type={self.exercise_type}, '
            f'language_level={self.language_level}, '
            f'topic={self.topic}, '
            f'exercise_text={self.exercise_text}, '
            f'data={self.data})'
        )
