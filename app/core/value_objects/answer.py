from typing import Any, Dict, List, Optional, Set, Type

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

    def __str__(self) -> str:
        return self.model_dump_json()


class FillInTheBlankAnswer(Answer):
    words: List[str] = Field(description='Words to fill in the blanks')

    def get_answer_text(self) -> str:
        return ';'.join(self.words)


class ChooseSentenceAnswer(Answer):
    sentence: str = Field(description='Chosen sentence')

    def get_answer_text(self) -> str:
        return self.sentence


class ChooseAccentAnswer(Answer):
    accent: str = Field(description='Chosen accent')

    def get_answer_text(self) -> str:
        return self.accent


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
    answer_type = data.get('type')
    if not isinstance(answer_type, str):
        raise ValueError('Missing or invalid "type" key in Answer data')

    answer_types: Dict[str, Type[Answer]] = {
        'FillInTheBlankAnswer': FillInTheBlankAnswer,
        'ChooseSentenceAnswer': ChooseSentenceAnswer,
        'ChooseAccentAnswer': ChooseAccentAnswer,
        'SentenceConstructionAnswer': SentenceConstructionAnswer,
        'MultipleChoiceAnswer': MultipleChoiceAnswer,
        'TranslationAnswer': TranslationAnswer,
    }

    answer_class: Optional[Type[Answer]] = answer_types.get(answer_type)
    if answer_class is None:
        raise ValueError(f'Unknown Answer type: {answer_type}')

    return answer_class.model_validate(data)
