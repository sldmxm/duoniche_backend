from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.core.value_objects.answer import (
    Answer,
    ChooseAccentAnswer,
    ChooseSentenceAnswer,
    FillInTheBlankAnswer,
    StoryComprehensionAnswer,
)
from app.utils import transliteration


class ExerciseData(ABC, BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    @abstractmethod
    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    @abstractmethod
    def to_cyrillic(self) -> ExerciseData:
        """Returns a new instance of the data with text fields
        transliterated to Cyrillic."""
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

    def to_cyrillic(self) -> FillInTheBlankExerciseData:
        new_data = self.model_copy(deep=True)
        new_data.text_with_blanks = transliteration.to_cyrillic(
            self.text_with_blanks
        )
        new_data.words = [transliteration.to_cyrillic(w) for w in self.words]
        return new_data


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

    def to_cyrillic(self) -> ChooseSentenceExerciseData:
        new_data = self.model_copy(deep=True)
        new_data.options = [
            transliteration.to_cyrillic(opt) for opt in self.options
        ]
        return new_data


class ChooseAccentExerciseData(ExerciseData):
    type: Literal['ChooseAccentExerciseData'] = Field(
        default='ChooseAccentExerciseData',
        description='Type of exercise data',
    )
    options: List[str] = Field(
        description='List of accents',
    )
    meaning: Optional[str] = Field(
        default=None,
        description='Meaning of the word',
    )

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        if not isinstance(answer, ChooseAccentAnswer):
            raise ValueError('Answer must be ChooseAccentAnswer')
        return answer.answer

    def to_cyrillic(self) -> ChooseAccentExerciseData:
        new_data = self.model_copy(deep=True)
        new_data.options = [
            transliteration.to_cyrillic(opt) for opt in self.options
        ]
        if new_data.meaning:
            new_data.meaning = transliteration.to_cyrillic(self.meaning)
        return new_data


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

    def to_cyrillic(self) -> StoryComprehensionExerciseData:
        new_data = self.model_copy(deep=True)
        new_data.content_text = transliteration.to_cyrillic(self.content_text)
        new_data.options = [
            transliteration.to_cyrillic(opt) for opt in self.options
        ]
        return new_data


class SentenceConstructionExerciseData(ExerciseData):
    type: Literal['SentenceConstructionExerciseData'] = Field(
        default='SentenceConstructionExerciseData',
        description='Type of exercise data',
    )
    words: List[str] = Field(description='List of words')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_cyrillic(self) -> SentenceConstructionExerciseData:
        raise NotImplementedError


class MultipleChoiceExerciseData(ExerciseData):
    type: Literal['MultipleChoiceExerciseData'] = Field(
        default='MultipleChoiceExerciseData',
        description='Type of exercise data',
    )
    options: List[str] = Field(description='List of options')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_cyrillic(self) -> MultipleChoiceExerciseData:
        raise NotImplementedError


class TranslationExerciseData(ExerciseData):
    type: Literal['TranslationExerciseData'] = Field(
        default='TranslationExerciseData', description='Type of exercise data'
    )
    translations: List[str] = Field(description='List of translations')

    def get_answered_by_user_exercise_text(self, answer: Answer) -> str:
        raise NotImplementedError

    def to_cyrillic(self) -> TranslationExerciseData:
        raise NotImplementedError
