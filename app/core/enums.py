from enum import Enum, auto


class ExerciseType(Enum):
    SENTENCE_CONSTRUCTION = 'sentence_construction'
    MULTIPLE_CHOICE = 'multiple_choice'
    FILL_IN_THE_BLANK = 'fill_in_the_blank'
    TRANSLATION = 'translation'


class LanguageLevel(Enum):
    BEGINNER = 'beginner'
    INTERMEDIATE = 'intermediate'
    ADVANCED = 'advanced'


class AttemptStatus(Enum):
    CORRECT = auto()
    INCORRECT = auto()
    PARTIALLY_CORRECT = auto()
