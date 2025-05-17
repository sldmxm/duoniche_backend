from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.core.value_objects.answer import (
    Answer,
    ChooseAccentAnswer,
    ChooseSentenceAnswer,
    FillInTheBlankAnswer,
)


class ExerciseData(ABC, BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    @property
    def type(self) -> str:
        return self.__class__.__name__

    @abstractmethod
    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        data = super().model_dump(**kwargs)
        data['type'] = self.type
        return data


class FillInTheBlankExerciseData(ExerciseData):
    text_with_blanks: str = Field(description='Text with blanks')
    words: List[str] = Field(description='List of words')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, FillInTheBlankAnswer):
            raise ValueError('Answer must be FillInTheBlankAnswer')

        words_count = len(answer.words)
        if words_count == 0:
            return self.text_with_blanks
        blanks = self.text_with_blanks.count(
            settings.exercise_fill_in_the_blank_blanks
        )
        if blanks == 0:
            return self.text_with_blanks

        parts = self.text_with_blanks.split(
            settings.exercise_fill_in_the_blank_blanks
        )
        result = ''
        for i in range(len(parts)):
            result += parts[i].replace('_', '')
            if i < len(answer.words):
                result += answer.words[i]

        return result


class ChooseSentenceExerciseData(ExerciseData):
    options: List[str] = Field(description='List of sentences')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, ChooseSentenceAnswer):
            raise ValueError('Answer must be ChooseSentenceAnswer')
        return answer.answer


class ChooseAccentExerciseData(ExerciseData):
    options: List[str] = Field(description='List of accents')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, ChooseAccentAnswer):
            raise ValueError('Answer must be ChooseAccentAnswer')
        return answer.answer


class SentenceConstructionExerciseData(ExerciseData):
    words: List[str] = Field(description='List of words')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


class MultipleChoiceExerciseData(ExerciseData):
    options: List[str] = Field(description='List of options')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


class TranslationExerciseData(ExerciseData):
    translations: List[str] = Field(description='List of translations')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


def create_exercise_data_model_validate(data: Dict[str, Any]) -> ExerciseData:
    exercise_data_type = data.get('type')
    if not isinstance(exercise_data_type, str):
        raise ValueError('Missing or invalid "type" key in ExerciseData data')

    exercise_data_types: Dict[str, Type[ExerciseData]] = {
        'FillInTheBlankExerciseData': FillInTheBlankExerciseData,
        'ChooseSentenceExerciseData': ChooseSentenceExerciseData,
        'ChooseAccentExerciseData': ChooseAccentExerciseData,
        'SentenceConstructionExerciseData': SentenceConstructionExerciseData,
        'MultipleChoiceExerciseData': MultipleChoiceExerciseData,
        'TranslationExerciseData': TranslationExerciseData,
    }

    exercise_data_class: Optional[Type[ExerciseData]] = (
        exercise_data_types.get(exercise_data_type)
    )
    if exercise_data_class is None:
        raise ValueError(f'Unknown ExerciseData type: {exercise_data_type}')

    return exercise_data_class.model_validate(data)
