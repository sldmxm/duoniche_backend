import pytest

from app.core.value_objects.answer import (
    FillInTheBlankAnswer,
    MultipleChoiceAnswer,
    SentenceConstructionAnswer,
    TranslationAnswer,
    create_answer_model_validate,
)
from app.core.value_objects.exercise import (
    FillInTheBlankExerciseData,
    MultipleChoiceExerciseData,
    SentenceConstructionExerciseData,
    TranslationExerciseData,
)


def test_sentence_construction_answer():
    answer = SentenceConstructionAnswer(sentences=['Test sentence.'])
    assert answer.sentences == ['Test sentence.']
    assert answer.type == 'SentenceConstructionAnswer'
    assert answer.get_answer_text() == 'Test sentence.'


def test_multiple_choice_answer():
    answer = MultipleChoiceAnswer(option_index={0})
    assert answer.option_index == {0}
    assert answer.type == 'MultipleChoiceAnswer'
    assert answer.get_answer_text() == '0'


def test_fill_in_the_blank_answer():
    answer = FillInTheBlankAnswer(words=['word1', 'word2'])
    assert answer.words == ['word1', 'word2']
    assert answer.type == 'FillInTheBlankAnswer'
    assert answer.get_answer_text() == 'word1;word2'


def test_translation_answer():
    answer = TranslationAnswer(translation='translation')
    assert answer.translation == 'translation'
    assert answer.type == 'TranslationAnswer'
    assert answer.get_answer_text() == 'translation'


def test_sentence_construction_exercise_data():
    data = SentenceConstructionExerciseData(words=['word1', 'word2'])
    assert data.words == ['word1', 'word2']


def test_multiple_choice_exercise_data():
    data = MultipleChoiceExerciseData(options=['option1', 'option2'])
    assert data.options == ['option1', 'option2']


def test_fill_in_the_blank_exercise_data():
    data = FillInTheBlankExerciseData(
        text_with_blanks='Test text', words=['word1', 'word2']
    )
    assert data.text_with_blanks == 'Test text'
    assert data.words == ['word1', 'word2']


def test_translation_exercise_data():
    data = TranslationExerciseData(translations=['source text'])
    assert data.translations == ['source text']


def test_sentence_construction_answer_serialization():
    answer = SentenceConstructionAnswer(sentences=['This', 'is', 'a', 'test'])
    data = answer.model_dump()
    restored = create_answer_model_validate(data)
    assert isinstance(restored, SentenceConstructionAnswer)
    assert restored.sentences == ['This', 'is', 'a', 'test']
    assert restored.get_answer_text() == 'This; is; a; test'
    assert restored.type == 'SentenceConstructionAnswer'


def test_multiple_choice_answer_serialization():
    answer = MultipleChoiceAnswer(option_index={1, 3})
    data = answer.model_dump()
    restored = create_answer_model_validate(data)
    assert isinstance(restored, MultipleChoiceAnswer)
    assert restored.option_index == {1, 3}
    assert restored.get_answer_text() == '1;3'
    assert restored.type == 'MultipleChoiceAnswer'


def test_fill_in_the_blank_answer_serialization():
    answer = FillInTheBlankAnswer(words=['word1', 'word2'])
    data = answer.model_dump()
    restored = create_answer_model_validate(data)
    assert isinstance(restored, FillInTheBlankAnswer)
    assert restored.words == ['word1', 'word2']
    assert restored.get_answer_text() == 'word1;word2'
    assert restored.type == 'FillInTheBlankAnswer'


def test_translation_answer_serialization():
    answer = TranslationAnswer(translation='translation')
    data = answer.model_dump()
    restored = create_answer_model_validate(data)
    assert isinstance(restored, TranslationAnswer)
    assert restored.translation == 'translation'
    assert restored.get_answer_text() == 'translation'
    assert restored.type == 'TranslationAnswer'


def test_answer_model_validate_invalid_type():
    with pytest.raises(ValueError, match='Unknown Answer type'):
        create_answer_model_validate({'type': 'InvalidType'})


def test_answer_model_validate_missing_type():
    with pytest.raises(
        ValueError, match='Missing or invalid "type" key in Answer data'
    ):
        create_answer_model_validate({})


def test_fill_in_the_blank_exercise_data_get_answered_by_user_exercise_text():
    data = FillInTheBlankExerciseData(
        text_with_blanks='This is a ____ test.', words=['great']
    )
    answer = FillInTheBlankAnswer(words=['great'])
    result = data.get_answered_by_user_exercise_text(answer)
    assert result == 'This is a great test.'

    data = FillInTheBlankExerciseData(
        text_with_blanks='____ is a ____ test.', words=['This', 'great']
    )
    answer = FillInTheBlankAnswer(words=['This', 'great'])
    result = data.get_answered_by_user_exercise_text(answer)
    assert result == 'This is a great test.'

    data = FillInTheBlankExerciseData(
        text_with_blanks='This is a test.', words=['great']
    )
    answer = FillInTheBlankAnswer(words=['great'])
    result = data.get_answered_by_user_exercise_text(answer)
    assert result == 'This is a test.'

    data = FillInTheBlankExerciseData(
        text_with_blanks='This is a ____ test.', words=['great']
    )
    answer = FillInTheBlankAnswer(words=[])
    result = data.get_answered_by_user_exercise_text(answer)
    assert result == 'This is a ____ test.'

    with pytest.raises(
        ValueError, match='Answer must be FillInTheBlankAnswer'
    ):
        data.get_answered_by_user_exercise_text(
            SentenceConstructionAnswer(sentences=['Test sentence.'])
        )
