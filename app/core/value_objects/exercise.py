from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.core.value_objects.answer import (
    Answer,
    ChooseAccentAnswer,
    ChooseSentenceAnswer,
    FillInTheBlankAnswer,
    StoryComprehensionAnswer,
)


class ExerciseData(ABC, BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    @abstractmethod
    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


class FillInTheBlankExerciseData(ExerciseData):
    type: Literal['FillInTheBlankExerciseData'] = Field(
        default='FillInTheBlankExerciseData',
        description='Type of exercise data',
    )
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
    type: Literal['ChooseSentenceExerciseData'] = Field(
        default='ChooseSentenceExerciseData',
        description='Type of exercise data',
    )
    options: List[str] = Field(description='List of sentences')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, ChooseSentenceAnswer):
            raise ValueError('Answer must be ChooseSentenceAnswer')
        return answer.answer


class ChooseAccentExerciseData(ExerciseData):
    type: Literal['ChooseAccentExerciseData'] = Field(
        default='ChooseAccentExerciseData', description='Type of exercise data'
    )
    options: List[str] = Field(description='List of accents')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, ChooseAccentAnswer):
            raise ValueError('Answer must be ChooseAccentAnswer')
        return answer.answer


class StoryComprehensionExerciseData(ExerciseData):
    type: Literal['StoryComprehensionExerciseData'] = Field(
        default='StoryComprehensionExerciseData',
        description='Type of exercise data',
    )
    content_text: str = Field(description='The full story text')
    audio_url: str = Field(description='The full story audio url')
    audio_telegram_file_id: str = Field(
        description='The full story audio telegram file_id'
    )
    options: List[str] = Field(
        description='List of statements, one is correct'
    )

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, StoryComprehensionAnswer):
            raise ValueError('Answer must be StoryComprehensionAnswer')
        return answer.answer


class SentenceConstructionExerciseData(ExerciseData):
    type: Literal['SentenceConstructionExerciseData'] = Field(
        default='SentenceConstructionExerciseData',
        description='Type of exercise data',
    )
    words: List[str] = Field(description='List of words')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


class MultipleChoiceExerciseData(ExerciseData):
    type: Literal['MultipleChoiceExerciseData'] = Field(
        default='MultipleChoiceExerciseData',
        description='Type of exercise data',
    )
    options: List[str] = Field(description='List of options')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError


class TranslationExerciseData(ExerciseData):
    type: Literal['TranslationExerciseData'] = Field(
        default='TranslationExerciseData', description='Type of exercise data'
    )
    translations: List[str] = Field(description='List of translations')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError
