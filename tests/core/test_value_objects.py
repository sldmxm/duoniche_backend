from app.core.value_objects.answer import (
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
