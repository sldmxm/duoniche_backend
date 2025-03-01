from dataclasses import dataclass
from typing import List


@dataclass
class ExerciseData: ...


@dataclass
class SentenceConstructionExerciseData(ExerciseData):
    words: List[str]


@dataclass
class MultipleChoiceExerciseData(ExerciseData):
    options: List[str]


@dataclass
class FillInTheBlankExerciseData(ExerciseData):
    text_with_blanks: str
    words: List[str]


@dataclass
class TranslationExerciseData(ExerciseData):
    source_language_text: str
