from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from pydantic import BaseModel, Field

from app.core.consts import EXERCISE_FILL_IN_THE_BLANK_BLANKS
from app.core.value_objects.answer import Answer, FillInTheBlankAnswer


class ExerciseData(ABC, BaseModel):
    @abstractmethod
    def get_full_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError


class SentenceConstructionExerciseData(ExerciseData):
    words: List[str] = Field(description='List of words')

    def get_full_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'SentenceConstructionExerciseData',
            'words': self.words,
        }


class MultipleChoiceExerciseData(ExerciseData):
    options: List[str] = Field(description='List of options')

    def get_full_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'MultipleChoiceExerciseData',
            'options': self.options,
        }


class FillInTheBlankExerciseData(ExerciseData):
    text_with_blanks: str = Field(description='Text with blanks')
    words: List[str] = Field(description='List of words')

    def get_full_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, FillInTheBlankAnswer):
            raise ValueError('Answer must be FillInTheBlankAnswer')

        words_count = len(answer.words)
        if words_count == 0:
            return self.text_with_blanks
        blanks = self.text_with_blanks.count(EXERCISE_FILL_IN_THE_BLANK_BLANKS)
        if blanks == 0:
            return self.text_with_blanks

        parts = self.text_with_blanks.split(EXERCISE_FILL_IN_THE_BLANK_BLANKS)
        result = ''
        for i in range(len(parts)):
            result += parts[i].replace('_', '')
            if i < len(answer.words):
                result += answer.words[i]

        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'FillInTheBlankExerciseData',
            'text_with_blanks': self.text_with_blanks,
            'words': self.words,
        }


class TranslationExerciseData(ExerciseData):
    translations: List[str] = Field(description='List of translations')

    def get_full_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'TranslationExerciseData',
            'translations': self.translations,
        }
