from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Type


class Answer(ABC):
    @abstractmethod
    def get_answer_text(self) -> str:
        """
        Returns a string representation of the answer.
        """
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        raise NotImplementedError

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Answer':
        """
        Constructs an Answer object from a dictionary.
        """
        answer_type = data.get('type')
        if not isinstance(answer_type, str):
            raise ValueError('Missing or invalid "type" key in Answer data')

        answer_types: Dict[str, Type[Answer]] = {
            'SentenceConstructionAnswer': SentenceConstructionAnswer,
            'MultipleChoiceAnswer': MultipleChoiceAnswer,
            'FillInTheBlankAnswer': FillInTheBlankAnswer,
            'TranslationAnswer': TranslationAnswer,
        }

        answer_class = answer_types.get(answer_type)
        if answer_class is None:
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
        sentences = data.get('sentences')
        if not isinstance(sentences, list):
            raise ValueError('"sentences" must be a list')
        return SentenceConstructionAnswer(sentences=sentences)


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
        option_index = data.get('option_index')
        if not isinstance(option_index, list):
            raise ValueError('"option_index" must be a list')
        return MultipleChoiceAnswer(option_index=set(option_index))


@dataclass
class FillInTheBlankAnswer(Answer):
    words: List[str]

    def get_answer_text(self) -> str:
        return ';'.join(self.words)

    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'FillInTheBlankAnswer', 'words': self.words}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'FillInTheBlankAnswer':
        words = data.get('words')
        if not isinstance(words, list):
            raise ValueError('"words" must be a list')
        return FillInTheBlankAnswer(words=words)


@dataclass
class TranslationAnswer(Answer):
    translations: List[str]

    def get_answer_text(self) -> str:
        return ';'.join(self.translations)

    def to_dict(self) -> Dict[str, Any]:
        return {'type': 'TranslationAnswer', 'translations': self.translations}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TranslationAnswer':
        translations = data.get('translations')
        if not isinstance(translations, list):
            raise ValueError('"translations" must be a list')
        return TranslationAnswer(translations=translations)
