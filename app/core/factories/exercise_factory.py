from typing import Any, Dict, Type

from app.core.entities.exercise import Exercise
from app.core.interfaces.exercise_type import ExerciseType


class ExerciseFactory:
    _exercise_types: Dict[str, Type[ExerciseType]] = {}

    @classmethod
    def register_exercise_type(
        cls, exercise_type: str, handler: Type[ExerciseType]
    ) -> None:
        cls._exercise_types[exercise_type] = handler

    @classmethod
    def get_handler(cls, exercise_type: str) -> ExerciseType:
        if exercise_type not in cls._exercise_types:
            raise ValueError(f'Unknown exercise type: {exercise_type}')

        return cls._exercise_types[exercise_type]()

    @classmethod
    def create_exercise(
        cls, exercise_type: str, **kwargs: Dict[str, Any]
    ) -> Exercise:
        handler = cls.get_handler(exercise_type)
        return handler.create_exercise(**kwargs)
