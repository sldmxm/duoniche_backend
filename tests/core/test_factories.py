import pytest

from app.core.enums import ExerciseType, LanguageLevel
from app.core.exercise_types.multiple_choice import MultipleChoiceExerciseType
from app.core.exercise_types.sentence_construction import (
    SentenceConstructionExerciseType,
)
from app.core.factories.exercise_factory import ExerciseFactory


def test_get_handler_sentence_construction():
    handler = ExerciseFactory.get_handler(
        ExerciseType.SENTENCE_CONSTRUCTION.value
    )
    assert isinstance(handler, SentenceConstructionExerciseType)


def test_get_handler_multiple_choice():
    handler = ExerciseFactory.get_handler(ExerciseType.MULTIPLE_CHOICE.value)
    assert isinstance(handler, MultipleChoiceExerciseType)


def test_get_handler_unknown_type():
    with pytest.raises(ValueError):
        ExerciseFactory.get_handler('unknown_type')


def test_create_exercise_sentence_construction():
    exercise = ExerciseFactory.create_exercise(
        exercise_type=ExerciseType.SENTENCE_CONSTRUCTION.value,
        language_level=LanguageLevel.BEGINNER.value,
        words=['this', 'is', 'a', 'test'],
    )
    assert exercise.exercise_type == ExerciseType.SENTENCE_CONSTRUCTION.value
    assert exercise.language_level == LanguageLevel.BEGINNER.value
    assert exercise.data.words == ['this', 'is', 'a', 'test']
