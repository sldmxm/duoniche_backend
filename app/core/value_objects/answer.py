from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Set


class Answer(ABC):
    @abstractmethod
    def get_answer_text(self) -> str:
        raise NotImplementedError


@dataclass
class SentenceConstructionAnswer(Answer):
    sentences: List[str]

    def get_answer_text(self) -> str:
        return ' '.join(self.sentences)


@dataclass
class MultipleChoiceAnswer(Answer):
    option_index: Set[int]

    def get_answer_text(self) -> str:
        return ' '.join(sorted(list(map(str, self.option_index))))


@dataclass
class FillInTheBlankAnswer(Answer):
    words: List[str]

    def get_answer_text(self) -> str:
        return ' '.join(self.words)


@dataclass
class TranslationAnswer(Answer):
    translations: List[str]

    def get_answer_text(self) -> str:
        return ' '.join(self.translations)
