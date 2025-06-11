import pytest

from app.config import settings
from app.core.entities.exercise import Exercise
from app.core.enums import ExerciseType, LanguageLevel
from app.core.generation.config import ExerciseTopic
from app.core.value_objects.answer import (
    ChooseSentenceAnswer,
    FillInTheBlankAnswer,
)
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.llm_service import LLMService

pytestmark = pytest.mark.asyncio

llm_service = LLMService(
    openai_api_key=settings.openai_api_key,
    model_name=settings.openai_test_model_name,
)


async def test_generate_fill_in_the_blank_exercise():
    exercise, answer = await llm_service.generate_exercise(
        user_language='ru',
        target_language='Bulgarian',
        language_level=LanguageLevel.B1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        topic=ExerciseTopic.GENERAL,
    )

    assert exercise.exercise_type == ExerciseType.FILL_IN_THE_BLANK
    assert exercise.data.text_with_blanks
    assert exercise.data.words
    assert isinstance(answer, FillInTheBlankAnswer)
    assert answer.words == exercise.data.words[: len(answer.words)]


async def test_generate_choose_sentence_exercise():
    exercise, answer = await llm_service.generate_exercise(
        user_language='ru',
        target_language='Bulgarian',
        language_level=LanguageLevel.B1,
        exercise_type=ExerciseType.CHOOSE_SENTENCE,
        topic=ExerciseTopic.GENERAL,
    )

    assert exercise.exercise_type == ExerciseType.CHOOSE_SENTENCE
    assert len(exercise.data.options) == 3
    assert isinstance(answer, ChooseSentenceAnswer)
    assert answer.answer in exercise.data.options


async def test_validate_attempt_correct():
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='English',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='The cat ___ on the mat.',
            words=['sat', 'run', 'jumped'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['sat'])
    is_correct, feedback = await llm_service.validate_attempt(
        user_language='ru',
        exercise=exercise,
        answer=answer,
    )

    assert is_correct is True
    assert feedback == ''


async def test_validate_attempt_incorrect():
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='Bulgarian',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='Аз обичам да ___ в парка.',
            words=['ходя', 'ходяа', 'гледам'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['ходяа'])
    is_correct, feedback = await llm_service.validate_attempt(
        user_language='ru',
        exercise=exercise,
        answer=answer,
    )

    assert is_correct is False
    assert feedback is not None
    assert feedback != ''


@pytest.mark.parametrize(
    'text_with_blanks, exercise_data_words, user_answer_words, '
    'expected_is_correct, case_description',
    [
        # Original cases
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['кухня', 'зал'],
            True,
            'Original: кухня и зал',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['кухня', 'сад'],
            True,
            'Original: кухня и сад (сад is plausible for огромный)',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['спальня', 'диван'],
            True,
            'Original: спальня и диван (диван is plausible for огромный)',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['спальня', 'кухня'],
            False,
            'Original: спальня и кухня (кухня for огромный is '
            'less plausible than зал/сад/диван)',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['кухня', 'спальня'],
            False,
            'Original: кухня и спальня (спальня for огромный '
            'is less plausible)',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['диван', 'зал'],
            False,
            'Original: диван и зал (диван for большая is incorrect type)',
        ),
        (
            'В моем доме большая ___ и огромный ___.',
            ['кухня', 'зал', 'диван', 'сад', 'спальня', 'крыльцо'],
            ['крыльцо', 'сад'],
            False,
            'Original: крыльцо и сад (крыльцо for большая is incorrect type)',
        ),
        (
            'Я сегодня много ___ и мало ___.',
            ['работал', 'отдыхал', 'спал', 'гулял'],
            ['работал', 'отдыхал'],
            True,
            'Word order: работал и отдыхал',
        ),
        (
            'Я сегодня много ___ и мало ___.',
            ['работал', 'отдыхал', 'спал', 'гулял'],
            ['отдыхал', 'работал'],
            True,
            'Word order: отдыхал и работал (semantically different, '
            'but grammatically fine)',
        ),
        (
            'Я сегодня много ___ и мало ___.',
            ['работал', 'отдыхал', 'спал', 'гулял'],
            ['спал', 'гулял'],
            True,
            'Word order: спал и гулял',
        ),
        (
            'Я сегодня много ___ и мало ___.',
            ['работал', 'отдыхал', 'спал', 'гулял'],
            ['работал', 'работал'],
            False,
            'Word order: работал и работал (repetitive, likely marked as '
            'less ideal or incorrect by LLM)',
        ),
        (
            '___ и ___ лежат на столе.',
            ['книга', 'ручка', 'телефон', 'ключи'],
            ['Книга', 'ручка'],
            True,
            'Objects: книга и ручка',
        ),
        (
            'На столе лежат ___ и ___.',
            ['книга', 'ручка', 'телефон', 'ключи'],
            ['телефон', 'ключи'],
            True,
            'Objects: телефон и ключи',
        ),
        (
            'На столе лежит ___ и ___.',
            ['книга', 'ручка', 'стол', 'стол'],
            ['стол', 'стол'],
            False,
            'Objects: стол и стол (sounds strange)',
        ),
    ],
)
async def test_validate_fill_in_the_blank_russian(
    text_with_blanks,
    exercise_data_words,
    user_answer_words,
    expected_is_correct,
    case_description,
):
    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='Russian',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text=f'Заполните пропуски: {text_with_blanks}',
        data=FillInTheBlankExerciseData(
            text_with_blanks=text_with_blanks,
            words=exercise_data_words,
        ),
    )

    answer = FillInTheBlankAnswer(words=user_answer_words)
    is_correct, feedback = await llm_service.validate_attempt(
        user_language='ru',
        exercise=exercise,
        answer=answer,
    )

    assert (
        is_correct is expected_is_correct
    ), f'Failed for: {case_description}\nFeedback: {feedback}'
    if not is_correct:
        assert feedback is not None


@pytest.mark.parametrize(
    'text_with_blanks, base_word_for_options, user_answer_word, '
    'expected_is_correct, case_description',
    [
        # --- Определенный артикль однозначно необходим ---
        (
            'Видях ___ на улицата.',
            'мъж',
            'мъжа',
            True,
            'Definite needed: Видях мъжа (I saw the man)',
        ),
        (
            'Видях ___ на улицата.',
            'мъж',
            'мъжът',
            False,
            'Definite needed but missing: Видях мъж '
            '(I saw a man - less likely in this context)',
        ),
        # --- Определенный артикль не нужен (или неверен) ---
        (
            'Това е един интересен ___.',
            'филм',
            'филм',
            True,
            'Definite not needed: Това е един интересен филм '
            '(This is an interesting film)',
        ),
        (
            'Това е един интересен ___.',
            'филм',
            'филмът',
            False,
            'Definite incorrect: Това е един интересен филмът',
        ),
        (
            'Искам ___ вода, моля.',
            'чаша',
            'чаша',
            True,
            'Definite not needed: Искам чаша вода '
            '(I want a glass of water)',
        ),
        (
            'Искам ___ вода, моля.',
            'чаша',
            'чашата',
            False,
            'Definite incorrect here: Искам чашата вода '
            '(implies specific glass, context missing)',
        ),
        # --- Неоднозначные случаи (оба варианта допустимы
        # благодаря снисходительным промптам) ---
        (
            'Кой написа ___?',
            'книга',
            'книгата',
            True,
            'Definite needed: Кой написа книгата? (Who wrote the book?)',
        ),
        (
            'Кой написа ___?',
            'книга',
            'книга',
            True,
            'Definite needed but missing: Кой написа книга?',
        ),
        (
            'Търся ___.',
            'книга',
            'книга',
            True,
            "Ambiguous: Търся книга (I'm looking for a book)",
        ),
        (
            'Търся ___.',
            'книга',
            'книгата',
            True,
            "Ambiguous: Търся книгата (I'm looking for the book)",
        ),
        (
            'Имаш ли ___?',
            'брат',
            'брат',
            True,
            'Ambiguous: Имаш ли брат? (Do you have a brother?)',
        ),
        (
            'Имаш ли ___?',
            'брат',
            'брата',
            False,
            'Ambiguous: Имаш ли брата? (Do you have the brother? - '
            'less common but possible if specific brother implied)',
        ),
        (
            '___ е здраве.',
            'Спорт',
            'Спортът',
            True,
            'Generic noun with article: Спортът е здраве '
            '(The sport is health - as a concept)',
        ),
        # --- Обобщенное существительное (артикль обычно не нужен,
        # но с ним тоже может быть смысл) ---
        (
            'Обичам ___.',
            'музика',
            'музика',
            True,
            'Generic noun: Обичам музика (I love music)',
        ),
        (
            'Обичам ___.',
            'музика',
            'музиката',
            True,
            'Generic noun with article: Обичам музиката '
            '(I love the music - specific or as a concept)',
        ),
        # --- Неправильная форма артикля ---
        (
            'Дай ми ___.',
            'ябълка',
            'ябълката',
            True,
            'Correct article form: Дай ми ябълката (f)',
        ),
        (
            'Дай ми ___.',
            'ябълка',
            'ябълкат',
            False,
            'Incorrect article form (m/n for f): Дай ми ябълкат',
        ),
        (
            'Това е ___.',
            'молив',
            'моливът',
            True,
            'Correct article form: Това е моливът (m)',
        ),
        (
            'Това е ___.',
            'молив',
            'молива',
            False,
            'Incorrect article form (f for m): Това е молива',
        ),
        (
            'Видях ___.',
            'момче',
            'момчето',
            True,
            'Correct article form: Видях момчето (n)',
        ),
        (
            'Видях ___.',
            'момче',
            'момче',
            True,
            'Correct article form: Видях момче',
        ),
        (
            'Той е добър ___.',
            'учител',
            'учителски',
            False,
            'Wrong part of speech: учителски (adj) instead of учител/учителят',
        ),
    ],
)
async def test_validate_bulgarian_articles(
    text_with_blanks,
    base_word_for_options,
    user_answer_word,
    expected_is_correct,
    case_description,
):
    exercise = Exercise(
        exercise_id=2,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK,
        exercise_language='Bulgarian',
        language_level=LanguageLevel.B1,
        topic=ExerciseTopic.GENERAL,
        exercise_text=f'Попълнете правилно члена: {text_with_blanks}',
        data=FillInTheBlankExerciseData(
            text_with_blanks=text_with_blanks,
            words=[
                base_word_for_options,
                base_word_for_options + 'та',
                base_word_for_options + 'ът',
                base_word_for_options + 'то',
                base_word_for_options + 'те',
            ],
        ),
    )

    answer = FillInTheBlankAnswer(words=[user_answer_word])

    is_correct, feedback = await llm_service.validate_attempt(
        user_language='ru',
        exercise=exercise,
        answer=answer,
    )

    assert is_correct is expected_is_correct, (
        f'Failed for: {case_description}\nFeedback: {feedback}',
    )
    if not is_correct:
        assert feedback is not None
        assert feedback != '', (
            f'Feedback should not be empty for incorrect answer:'
            f' {case_description}'
        )
