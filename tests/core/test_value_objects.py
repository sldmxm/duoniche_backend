import pytest

from app.core.value_objects.answer import (
    Answer,
    FillInTheBlankAnswer,
    MultipleChoiceAnswer,
    SentenceConstructionAnswer,
    TranslationAnswer,
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


def test_multiple_choice_answer():
    answer = MultipleChoiceAnswer(option_index={0})
    assert answer.option_index == {0}


def test_fill_in_the_blank_answer():
    answer = FillInTheBlankAnswer(words=['word1', 'word2'])
    assert answer.words == ['word1', 'word2']


def test_translation_answer():
    answer = TranslationAnswer(translations=['translation1', 'translation2'])
    assert answer.translations == ['translation1', 'translation2']


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
    data = TranslationExerciseData(source_language_text='source text')
    assert data.source_language_text == 'source text'


def test_sentence_construction_answer_serialization():
    answer = SentenceConstructionAnswer(sentences=['This', 'is', 'a', 'test'])
    data = answer.to_dict()
    restored = Answer.from_dict(data)
    assert isinstance(restored, SentenceConstructionAnswer)
    assert restored.sentences == ['This', 'is', 'a', 'test']
    assert restored.get_answer_text() == 'This;is;a;test'


def test_multiple_choice_answer_serialization():
    answer = MultipleChoiceAnswer(option_index={1, 3})
    data = answer.to_dict()
    restored = Answer.from_dict(data)
    assert isinstance(restored, MultipleChoiceAnswer)
    assert restored.option_index == {1, 3}
    assert restored.get_answer_text() == '1;3'


def test_answer_from_dict_invalid_type():
    with pytest.raises(ValueError, match='Unknown Answer type'):
        Answer.from_dict({'type': 'InvalidType'})


def test_answer_from_dict_missing_type():
    with pytest.raises(ValueError, match='Missing.*type.*key'):
        Answer.from_dict({})
