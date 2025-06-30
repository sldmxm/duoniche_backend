from typing import Any, Callable, Dict, List, Optional, Set, Type

from pydantic import BaseModel, ConfigDict, Field


class Answer(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
    )

    @property
    def type(self) -> str:
        return self.__class__.__name__

    def model_dump(self, **kwargs):
        data = super().model_dump(**kwargs)
        data['type'] = self.type
        return data

    def get_answer_text(self) -> str:
        """
        Returns a string representation of the answer.
        """
        raise NotImplementedError

    def get_transliterated_copy(
        self, translit_func: Callable[[str], str]
    ) -> 'Answer':
        """
        Returns a new, transliterated copy of the answer object.
        By default, it returns an unmodified deep copy.
        """
        raise NotImplementedError

    def __str__(self) -> str:
        return self.model_dump_json()


class FillInTheBlankAnswer(Answer):
    words: List[str] = Field(description='Words to fill in the blanks')

    def get_answer_text(self) -> str:
        return ';'.join(self.words)

    def get_transliterated_copy(
        self, translit_func: Callable[[str], str]
    ) -> 'FillInTheBlankAnswer':
        new_copy = self.model_copy(deep=True)
        new_copy.words = [translit_func(word) for word in new_copy.words]
        return new_copy


class ChooseOneAnswer(Answer):
    answer: str = Field(description='Chosen answer')

    def get_answer_text(self) -> str:
        return self.answer

    def get_transliterated_copy(
        self, translit_func: Callable[[str], str]
    ) -> 'ChooseOneAnswer':
        new_copy = self.model_copy(deep=True)
        new_copy.answer = translit_func(new_copy.answer)
        return new_copy


class ChooseSentenceAnswer(ChooseOneAnswer):
    answer: str = Field(description='Chosen sentence')


class ChooseAccentAnswer(ChooseOneAnswer):
    answer: str = Field(description='Chosen accent')


class StoryComprehensionAnswer(ChooseOneAnswer):
    answer: str = Field(description='Chosen statement about the story')


class SentenceConstructionAnswer(Answer):
    sentences: List[str] = Field(description='Constructed sentences')

    def get_answer_text(self) -> str:
        return '; '.join(self.sentences)


class MultipleChoiceAnswer(Answer):
    option_index: Set[int] = Field(description='Selected choice')

    def get_answer_text(self) -> str:
        return ';'.join(sorted(list(map(str, self.option_index))))


class TranslationAnswer(Answer):
    translation: str = Field(description='Translated text')

    def get_answer_text(self) -> str:
        return self.translation


def create_answer_model_validate(data: Dict[str, Any]) -> Answer:
    if 'type' in data:
        answer_type = data.get('type')
    else:
        answer_type_by_exercise: Dict[str, str] = {
            'fill_in_the_blank': 'FillInTheBlankAnswer',
            'choose_sentence': 'ChooseSentenceAnswer',
            'choose_accent': 'ChooseAccentAnswer',
            'story_comprehension': 'StoryComprehensionAnswer',
        }
        exercise_type = data.get('exercise_type')
        if exercise_type is not None:
            answer_type = answer_type_by_exercise.get(exercise_type)
        else:
            answer_type = None

    if not answer_type or not isinstance(answer_type, str):
        raise ValueError(
            'Missing or invalid "type"/"exercise_type" key in Answer data'
        )

    answer_types: Dict[str, Type[Answer]] = {
        'FillInTheBlankAnswer': FillInTheBlankAnswer,
        'ChooseSentenceAnswer': ChooseSentenceAnswer,
        'ChooseAccentAnswer': ChooseAccentAnswer,
        'StoryComprehensionAnswer': StoryComprehensionAnswer,
        'SentenceConstructionAnswer': SentenceConstructionAnswer,
        'MultipleChoiceAnswer': MultipleChoiceAnswer,
        'TranslationAnswer': TranslationAnswer,
    }

    answer_class: Optional[Type[Answer]] = answer_types.get(answer_type)
    if answer_class is None:
        raise ValueError(f'Unknown Answer type: {answer_type}')

    return answer_class.model_validate(data)
