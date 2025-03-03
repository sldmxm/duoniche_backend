import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Type


class Answer(ABC):
    @abstractmethod
    def get_answer_text(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Answer':
        answer_types: Dict[str, Type[Answer]] = {
            'SentenceConstructionAnswer': SentenceConstructionAnswer,
            'MultipleChoiceAnswer': MultipleChoiceAnswer,
            'FillInTheBlankAnswer': FillInTheBlankAnswer,
            'TranslationAnswer': TranslationAnswer,
        }
        answer_type = data.get('type')
        if not answer_type:
            raise ValueError(f'Missing "type" key in Answer data: {data}')
        answer_class = answer_types.get(answer_type)

        if not answer_class:
            raise ValueError(f'Unknown Answer type: {answer_type}')

        return answer_class.from_dict(data)

    def __str__(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class SentenceConstructionAnswer(Answer):
    sentences: List[str]

    def get_answer_text(self) -> str:
        return ';'.join(self.sentences)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'SentenceConstructionAnswer',
            'sentences': self.sentences,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'SentenceConstructionAnswer':
        return SentenceConstructionAnswer(sentences=data.get('sentences', []))


@dataclass
class MultipleChoiceAnswer(Answer):
    option_index: Set[int]

    def get_answer_text(self) -> str:
        return ';'.join(sorted(list(map(str, self.option_index))))

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'MultipleChoiceAnswer',
            'option_index': list(self.option_index),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MultipleChoiceAnswer':
        return MultipleChoiceAnswer(
            option_index=set(data.get('option_index', []))
        )


@dataclass
class FillInTheBlankAnswer(Answer):
    words: List[str]

    def get_answer_text(self) -> str:
        return ';'.join(self.words)

    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'FillInTheBlankAnswer', 'words': self.words}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FillInTheBlankAnswer':
        return FillInTheBlankAnswer(words=data.get('words', []))


@dataclass
class TranslationAnswer(Answer):
    translations: List[str]

    def get_answer_text(self) -> str:
        return ';'.join(self.translations)

    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'TranslationAnswer', 'translations': self.translations}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TranslationAnswer':
        return TranslationAnswer(translations=data.get('translations', []))
