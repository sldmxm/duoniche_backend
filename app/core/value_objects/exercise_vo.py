from dataclasses import dataclass
from typing import List


@dataclass
class ExerciseData: ...


@dataclass
class SentenceConstructionExerciseData(ExerciseData):
    words: List[str]
    correct_sentence: str


@dataclass
class MultipleChoiceExerciseData(ExerciseData):
    options: List[str]
    correct_option_index: int


@dataclass
class FillInTheBlankExerciseData(ExerciseData):
    text_with_blanks: str
    correct_words: List[str]


@dataclass
class TranslationExerciseData(ExerciseData):
    source_language_text: str
    target_language_text: str
