import pytest

from app.core.entities.exercise import Exercise
from app.core.entities.user import User
from app.core.enums import ExerciseType
from app.core.value_objects.answer import FillInTheBlankAnswer
from app.core.value_objects.exercise import FillInTheBlankExerciseData
from app.llm.llm_service import LLMService

pytestmark = pytest.mark.asyncio


@pytest.fixture()
def user():
    return User(
        user_id=1,
        telegram_id=123,
        username='testuser',
        name='Test User',
        user_language='russian',
        target_language='bulgarian',
    )


async def test_generate_fill_in_the_blank_exercise(user):
    llm_service = LLMService()

    try:
        exercise, answer = await llm_service.generate_exercise(
            user, 'beginner', ExerciseType.FILL_IN_THE_BLANK.value
        )
    except ValueError:
        return

    assert exercise.exercise_type == ExerciseType.FILL_IN_THE_BLANK.value
    assert exercise.data.text_with_blanks
    assert exercise.data.words
    assert isinstance(answer, FillInTheBlankAnswer)


async def test_validate_attempt_correct(user):
    llm_service = LLMService()

    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level='beginner',
        topic='general',
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='The cat ___ on the mat.',
            words=['sat', 'run', 'jumped'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['sat'])
    correct_answers = [FillInTheBlankAnswer(words=['sat'])]
    is_correct, feedback = await llm_service.validate_attempt(
        user, exercise, answer, correct_answers
    )

    assert is_correct is True
    assert feedback == ''


async def test_validate_attempt_incorrect(user):
    llm_service = LLMService()

    exercise = Exercise(
        exercise_id=1,
        exercise_type=ExerciseType.FILL_IN_THE_BLANK.value,
        exercise_language='en',
        language_level='beginner',
        topic='general',
        exercise_text='Fill in the blank',
        data=FillInTheBlankExerciseData(
            text_with_blanks='Аз обичам да ___ в парка.',
            words=['ходя', 'ходяа', 'гледам'],
        ),
    )

    answer = FillInTheBlankAnswer(words=['гледам'])
    correct_answers = [FillInTheBlankAnswer(words=['ходя'])]
    is_correct, feedback = await llm_service.validate_attempt(
        user, exercise, answer, correct_answers
    )

    assert is_correct is False
    assert feedback is not None
